import json
import math
import uuid
from io import BytesIO
from decimal import Decimal, InvalidOperation
from PIL import Image, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.urls import reverse
from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from table.models import Table, BarProduct
from session.models import Session


def product_data(product):
    return {'id': product.id, 'name': product.name, 'category': product.category,
            'price': str(product.price), 'stock': product.stock,
            'image_url': reverse('product_image', args=[product.id]) + '?v=' + product.image.name.rsplit('/', 1)[-1] if product.image else ''}


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from session.models import settle_expired_sessions
        settle_expired_sessions()
        tables = list(Table.objects.order_by('number'))
        context['table_data'] = [{
            'id': t.id, 'number': t.number, 'type': t.table_type, 'name': t.display_name, 'rate': str(t.price_per_hour),
            'x': t.position_x, 'y': t.position_y, 'rotation': t.rotation,
            'start': next((s.start_time.isoformat() for s in t.sessions.filter(status='active') if s.start_time), None),
        } for t in tables]
        from table.reservations import reservation_data
        for entry, table in zip(context['table_data'], tables):
            entry['reservations'] = reservation_data(table.id)
            active = table.sessions.filter(status='active').first()
            entry.update({'deadline': active.scheduled_end.isoformat() if active and active.scheduled_end else None,
                          'billing_type': active.billing_type if active else 'metered',
                          'prepaid_amount': str(active.prepaid_amount) if active else '0',
                          'session_id': active.id if active else None})
        context['products'] = [product_data(p) for p in BarProduct.objects.all()]
        context['unpaid_sessions'] = Session.objects.filter(payment_done=False, status='stopped').select_related('table').order_by('-end_time')
        from django.db.models import Q
        from table.models import BarSale
        today = timezone.localdate()
        context['paid_sessions'] = Session.objects.filter(payment_done=True).filter(Q(paid_at__date=today) | Q(paid_at__isnull=True, end_time__date=today)).select_related('table').order_by('-paid_at', '-end_time')
        context['bar_sales'] = BarSale.objects.filter(payment_done=True, sold_at__date=today).select_related('table').prefetch_related('items')
        context['unpaid_bar_sales'] = BarSale.objects.filter(payment_done=False).select_related('table').prefetch_related('items')
        context['total_income'] = sum(s.total_price for s in context['paid_sessions']) + sum(s.total for s in context['bar_sales'])
        # One receipt per game; unrelated bar purchases keep their own receipt.
        from table.billing import bill_data
        pending_ids = set(context['unpaid_sessions'].values_list('id', flat=True))
        pending_ids.update(s.session_id for s in context['unpaid_bar_sales'] if s.session_id)
        paid_ids = set(s.id for s in context['paid_sessions'])
        paid_ids.update(s.session_id for s in context['bar_sales'] if s.session_id)
        def receipt_rows(ids, standalone):
            rows = []
            for session in Session.objects.filter(id__in=ids).prefetch_related('bar_orders__items', 'bar_orders__table').order_by('-start_time'):
                row = bill_data(session, session.bar_orders.all())
                row.update(kind='session', id=session.id)
                rows.append(row)
            for sale in standalone:
                if sale.session_id is None:
                    row = bill_data(sales=[sale])
                    row.update(kind='sale', id=sale.id)
                    rows.append(row)
            return rows
        context['pending_bills'] = receipt_rows(pending_ids, context['unpaid_bar_sales'])
        context['paid_bills'] = receipt_rows(paid_ids - pending_ids, context['bar_sales'])
        context['active_count'] = sum(bool(t['start']) for t in context['table_data'])
        context['free_count'] = len(tables) - context['active_count']
        return context


@method_decorator(staff_member_required, name='dispatch')
class LayoutView(View):
    def post(self, request):
        try:
            rows = json.loads(request.body)['tables']
            tables = {t.id: t for t in Table.objects.all()}
            if not isinstance(rows, list) or len(rows) != len(tables) or {r['id'] for r in rows} != set(tables):
                raise ValueError()
            for row in rows:
                x, y = float(row['x']), float(row['y'])
                rotation = int(row['rotation'])
                if not math.isfinite(x) or not math.isfinite(y) or not 15 <= x <= 85 or not 12 <= y <= 88 or rotation not in (0, 90, 180, 270):
                    raise ValueError()
                t = tables[row['id']]
                t.position_x, t.position_y, t.rotation = x, y, rotation
            with transaction.atomic():
                Table.objects.bulk_update(tables.values(), ['position_x', 'position_y', 'rotation'])
            return JsonResponse({'success': True})
        except (ValueError, KeyError, TypeError, OverflowError):
            return JsonResponse({'error': 'Joylashuv qiymatlarini tekshiring.'}, status=400)


@method_decorator(staff_member_required, name='dispatch')
class ProductView(View):
    def post(self, request):
        try:
            data = request.POST if request.content_type == 'multipart/form-data' else json.loads(request.body)
            name, category = str(data['name']).strip(), str(data['category']).strip()
            price = Decimal(str(data['price']))
            stock = int(data['stock'])
            if not name or len(name) > 100 or not category or len(category) > 50 or not price.is_finite() or price < 0 or price > 9999999999 or price != price.to_integral_value() or stock < 0 or stock > 2147483647:
                raise ValueError()
            product = get_object_or_404(BarProduct, pk=data['id']) if data.get('id') else BarProduct()
            upload = request.FILES.get('image')
            processed_image = None
            if upload:
                if upload.size > 5 * 1024 * 1024:
                    return JsonResponse({'error': 'Rasm hajmi 5 MB dan oshmasin.'}, status=400)
                try:
                    with Image.open(upload) as picture:
                        if picture.format not in ('JPEG', 'PNG', 'WEBP') or picture.width * picture.height > 16000000:
                            raise ValueError()
                        picture.load()
                        picture = picture.convert('RGB')
                        picture.thumbnail((1200, 1200))
                        buffer = BytesIO()
                        picture.save(buffer, format='WEBP', quality=85)
                        processed_image = ContentFile(buffer.getvalue(), name=f'{uuid.uuid4().hex}.webp')
                except (ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError):
                    return JsonResponse({'error': 'JPG, PNG yoki WebP rasm yuklang (16 megapikselgacha).'}, status=400)
            old_image = product.image.name
            if processed_image:
                product.image = processed_image
            elif data.get('remove_image') in ('true', 'on', True):
                product.image = ''
            product.name, product.category, product.price, product.stock = name, category, price, stock
            product.save()
            if old_image and old_image != product.image.name:
                product.image.storage.delete(old_image)
            return JsonResponse({'success': True, 'product': product_data(product)})
        except (ValueError, KeyError, TypeError, InvalidOperation, OverflowError):
            return JsonResponse({'error': 'Mahsulot ma’lumotlarini to‘g‘ri kiriting.'}, status=400)


@method_decorator(staff_member_required, name='dispatch')
class ProductImageView(View):
    def get(self, request, product_id):
        product = get_object_or_404(BarProduct, pk=product_id)
        if not product.image:
            from django.http import Http404
            raise Http404()
        try:
            return FileResponse(product.image.open('rb'), content_type='image/webp')
        except FileNotFoundError:
            from django.http import Http404
            raise Http404()


class SettingsView(DashboardView):
    template_name = 'settings.html'

    def post(self, request):
        error = None
        try:
            with transaction.atomic():
                for table in Table.objects.select_for_update().order_by('number'):
                    rate = Decimal(request.POST[f'rate_{table.id}'])
                    if not rate.is_finite() or rate < 0 or rate > 9999999999 or rate != rate.to_integral_value():
                        raise ValueError('Narxni musbat butun son bilan kiriting.')
                    if rate != table.price_per_hour:
                        if table.sessions.filter(status='active').exists():
                            raise ValueError(f'{table.number}-stolda o‘yin davom etmoqda. Tarifni o‘yin tugagach o‘zgartiring.')
                        table.price_per_hour = rate
                        table.save(update_fields=['price_per_hour'])
        except (ValueError, InvalidOperation, KeyError) as exc:
            error = str(exc) if isinstance(exc, ValueError) else 'Barcha tariflarni to‘g‘ri kiriting.'
        context = self.get_context_data()
        context['error'] = error
        context['success'] = not error
        return self.render_to_response(context, status=400 if error else 200)


@method_decorator(staff_member_required, name='dispatch')
class BarSaleView(View):
    def post(self, request):
        from table.models import BarSale, BarSaleItem
        from django.db.models import F
        try:
            data = json.loads(request.body)
            key = uuid.UUID(data['request_key'])
            items = data['items']
            if not isinstance(items, list) or not 1 <= len(items) <= 100:
                raise ValueError()
            quantities = {}
            for row in items:
                product_id, quantity = int(row['id']), int(row['quantity'])
                if isinstance(row['quantity'], bool) or str(quantity) != str(row['quantity']) or not 1 <= quantity <= 1000 or product_id in quantities:
                    raise ValueError()
                quantities[product_id] = quantity
            with transaction.atomic():
                previous = BarSale.objects.filter(request_key=key).first()
                if previous:
                    return JsonResponse({'success': True, 'sale_id': previous.id, 'total': str(previous.total), 'products': [product_data(p) for p in BarProduct.objects.all()]})
                device = get_object_or_404(Table, pk=data['table_id']) if data.get('table_id') else None
                linked_session = None
                if data.get('session_id'):
                    linked_session = get_object_or_404(Session.objects.select_for_update(), pk=data['session_id'], table=device)
                    if linked_session.status != 'active':
                        return JsonResponse({'error': 'O‘yin yakunlangan. Stolni qayta tanlang.'}, status=409)
                elif device:
                    linked_session = device.sessions.select_for_update().filter(status='active').first()
                deferred = data.get('defer_payment') is True
                products = list(BarProduct.objects.select_for_update().filter(id__in=quantities))
                if len(products) != len(quantities):
                    raise ValueError()
                total = sum(p.price * quantities[p.id] for p in products)
                if total > 999999999999:
                    raise ValueError()
                # Conditional writes also enforce stock availability on SQLite.
                for p in products:
                    quantity = quantities[p.id]
                    if not BarProduct.objects.filter(pk=p.pk, stock__gte=quantity).update(stock=F('stock') - quantity):
                        raise ValueError(f'{p.name}: qoldiq yetarli emas.')
                sale = BarSale.objects.create(table=device, session=linked_session, total=total, request_key=key, payment_done=not deferred)
                BarSaleItem.objects.bulk_create([BarSaleItem(sale=sale, product=p, name=p.name, unit_price=p.price, quantity=quantities[p.id]) for p in products])
            return JsonResponse({'success': True, 'sale_id': sale.id, 'total': str(total), 'products': [product_data(p) for p in BarProduct.objects.all()]})
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            return JsonResponse({'error': str(exc) if isinstance(exc, ValueError) and str(exc) else 'Sotuv ma’lumotlarini tekshiring.'}, status=400)


@method_decorator(staff_member_required, name='dispatch')
class PayBarSaleView(View):
    @transaction.atomic
    def post(self, request, sale_id):
        from table.models import BarSale
        sale = get_object_or_404(BarSale.objects.select_for_update(), pk=sale_id)
        if sale.payment_done:
            return JsonResponse({'error': 'Bu bar hisobi allaqachon to‘langan.'}, status=409)
        sale.payment_done = True
        sale.sold_at = timezone.now()
        sale.save(update_fields=['payment_done', 'sold_at'])
        return JsonResponse({'success': True})
