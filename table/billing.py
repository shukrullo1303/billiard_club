import json
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from session.models import Session
from .models import BarSale


def bill_data(session=None, sales=()):
    sales = list(sales)
    game = session.calculate_total(live=True) if session and session.status == 'active' else (session.total_price if session else Decimal('0'))
    bar = sum((s.total for s in sales), Decimal('0'))
    paid = (game if session and session.payment_done else Decimal('0')) + sum((s.total for s in sales if s.payment_done), Decimal('0'))
    return {
        'success': True, 'name': session.device_name if session else (sales[0].table.display_name if sales and sales[0].table else 'Bar'),
        'session_id': session.id if session else None, 'table_id': session.table_id if session else None,
        'active': bool(session and session.status == 'active'),
        'start': session.start_time.isoformat() if session and session.start_time else None,
        'end': session.end_time.isoformat() if session and session.end_time else None,
        'seconds': max(0, int(((session.end_time or timezone.now()) - session.start_time).total_seconds())) if session and session.start_time else 0,
        'game': str(game), 'bar': str(bar), 'total': str(game + bar), 'paid': str(paid), 'due': str(game + bar - paid),
        'unpaid_sales': sorted(s.id for s in sales if not s.payment_done),
        'items': [{'order': s.id, 'name': i.name, 'quantity': i.quantity, 'price': str(i.unit_price), 'total': str(i.unit_price * i.quantity), 'paid': s.payment_done} for s in sales for i in s.items.all()],
    }


@method_decorator(staff_member_required, name='dispatch')
class BillView(View):
    def objects(self, kind, pk, lock=False):
        if kind == 'session':
            query = Session.objects.select_for_update() if lock else Session.objects.all()
            session = get_object_or_404(query, pk=pk)
            sales = session.bar_orders.select_related('table').prefetch_related('items')
        else:
            session = None
            sales = BarSale.objects.select_related('table').prefetch_related('items').filter(pk=pk)
            get_object_or_404(sales, pk=pk, session__isnull=True)
        if lock:
            sales = sales.select_for_update()
        return session, list(sales)

    def get(self, request, kind, pk):
        return JsonResponse(bill_data(*self.objects(kind, pk)))

    @transaction.atomic
    def post(self, request, kind, pk):
        session, sales = self.objects(kind, pk, lock=True)
        bill = bill_data(session, sales)
        if bill['active']:
            return JsonResponse({'error': 'Avval o‘yinni yakunlang.'}, status=409)
        if (not session or session.payment_done) and not bill['unpaid_sales']:
            return JsonResponse({'error': 'Bu hisob allaqachon to‘langan.'}, status=409)
        try:
            expected = json.loads(request.body)
            if Decimal(str(expected['due'])) != Decimal(bill['due']) or expected['unpaid_sales'] != bill['unpaid_sales']:
                raise ValueError()
        except (ValueError, KeyError, TypeError, ArithmeticError):
            return JsonResponse({'error': 'Hisob o‘zgardi. Tafsilotlarni qayta oching.'}, status=409)
        now = timezone.now()
        if session and not session.payment_done:
            session.payment_done = True
            session.paid_at = now
            session.save(update_fields=['payment_done', 'paid_at'])
        BarSale.objects.filter(pk__in=bill['unpaid_sales']).update(payment_done=True, sold_at=now)
        return JsonResponse({'success': True, 'paid': bill['due']})
