import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_CEILING

from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View

from table.models import Table
from .models import Session, settle_expired_sessions


def prepaid_terms(data, rate):
    """Validate a single prepaid option and return its amount and duration."""
    if rate <= 0:
        raise ValueError('Oldindan to‘lov uchun musbat soatlik tarif belgilang.')
    minutes = data.get('prepaid_minutes')
    amount_value = data.get('prepaid_amount')
    if (minutes is not None) == (amount_value is not None):
        raise ValueError('30/60 daqiqa yoki to‘lov summasidan birini tanlang.')
    if minutes is not None:
        if isinstance(minutes, bool) or str(minutes) not in ('30', '60'):
            raise ValueError('Oldindan to‘lov vaqti 30 yoki 60 daqiqa bo‘lishi kerak.')
        duration = timedelta(minutes=int(minutes))
        amount = (rate * Decimal(str(minutes)) / Decimal('60')).to_integral_value(rounding=ROUND_CEILING)
    else:
        try:
            if isinstance(amount_value, bool):
                raise InvalidOperation
            amount = Decimal(str(amount_value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError('Oldindan to‘lov summasini to‘g‘ri kiriting.')
        if not amount.is_finite() or amount <= 0 or amount > Decimal('9999999999') or amount != amount.to_integral_value():
            raise ValueError('Oldindan to‘lovni musbat, butun so‘mda kiriting.')
        microseconds = int(amount * Decimal('3600000000') / rate)
        try:
            duration = timedelta(microseconds=max(1, microseconds))
        except OverflowError:
            raise ValueError('Bu summa uchun o‘yin muddati juda katta.')
    if amount > Decimal('9999999999'):
        raise ValueError('Oldindan to‘lov summasi juda katta.')
    return amount, duration


@method_decorator(staff_member_required, name='dispatch')
class StartSessionView(View):
    @transaction.atomic
    def post(self, request, table_id):
        now = timezone.now()
        settle_expired_sessions(now)
        table = get_object_or_404(Table.objects.select_for_update(), id=table_id)
        if table.sessions.filter(status='active').exists():
            return JsonResponse({'error': 'Bu stolda o‘yin allaqachon boshlangan.'}, status=409)
        try:
            data = (json.loads(request.body) if request.body else {}) if request.content_type == 'application/json' else request.POST.dict()
            if not isinstance(data, dict):
                raise ValueError('O‘yin ma’lumotlarini tekshiring.')
            mode = data.get('mode', 'metered')
            if mode not in ('metered', 'prepaid'):
                raise ValueError('To‘lov turini to‘g‘ri tanlang.')
            if table.price_per_hour <= 0:
                raise ValueError('O‘yinni boshlash uchun musbat soatlik tarif belgilang.')
            amount, deadline = Decimal('0'), None
            if mode == 'prepaid':
                amount, duration = prepaid_terms(data, table.price_per_hour)
                deadline = now + duration
        except (ValueError, OverflowError) as exc:
            error = 'O‘yin ma’lumotlarini tekshiring.' if isinstance(exc, (json.JSONDecodeError, OverflowError)) else str(exc)
            return JsonResponse({'error': error}, status=400)
        from table.reservations import reservation_data
        reservations = reservation_data(table.id)
        if reservations and data.get('reservation_ack') != [r['id'] for r in reservations]:
            return JsonResponse({'error': 'Bronni tekshiring va boshlashni yana bosing.', 'reservations': reservations}, status=409)
        session = Session.objects.create(
            table=table, start_time=now, status='active', billing_type=mode,
            prepaid_amount=amount, scheduled_end=deadline,
            total_price=amount, payment_done=mode == 'prepaid',
            paid_at=now if mode == 'prepaid' else None,
        )
        table.is_active = True
        table.save(update_fields=['is_active'])
        return JsonResponse({
            'success': True, 'start_time': session.start_time.isoformat(), 'session_id': session.id,
            'deadline': deadline.isoformat() if deadline else None, 'billing_type': mode,
            'prepaid_amount': str(amount), 'payment_done': session.payment_done,
        })


@method_decorator(staff_member_required, name='dispatch')
class StopSessionView(View):
    @transaction.atomic
    def post(self, request, table_id):
        now = timezone.now()
        settle_expired_sessions(now)
        table = get_object_or_404(Table.objects.select_for_update(), id=table_id)
        session = table.sessions.select_for_update().filter(status='active').first()
        if not session:
            return JsonResponse({'error': 'Bu stolda faol o‘yin yo‘q.'}, status=409)
        session.end_time = now
        session.total_price = session.calculate_total(live=True, at=now)
        session.status = 'stopped'
        session.save(update_fields=['end_time', 'status', 'total_price'])
        table.is_active = False
        table.save(update_fields=['is_active'])
        return JsonResponse({
            'success': True,
            'session': {
                'id': session.id, 'table_number': table.number, 'table_type': table.table_type,
                'device_name': session.device_name,
                'price': session.total_price, 'billing_type': session.billing_type,
                'payment_done': session.payment_done,
            },
        })


@method_decorator(staff_member_required, name='dispatch')
class PaySessionView(View):
    @transaction.atomic
    def post(self, request, session_id):
        session = get_object_or_404(Session.objects.select_for_update(), id=session_id)
        if session.status != 'stopped' or session.payment_done or session.billing_type != 'metered':
            return JsonResponse({'error': 'Faqat yakunlangan, to‘lanmagan o‘yin uchun to‘lash mumkin.'}, status=409)
        session.payment_done = True
        session.paid_at = timezone.now()
        session.save(update_fields=['payment_done', 'paid_at'])
        today = timezone.localdate()
        total_income = Session.objects.filter(payment_done=True).filter(
            Q(paid_at__date=today) | Q(paid_at__isnull=True, end_time__date=today)
        ).aggregate(s=Sum('total_price'))['s'] or 0
        return JsonResponse({'success': True, 'total_income': total_income})


@method_decorator(staff_member_required, name='dispatch')
class StateView(View):
    def get(self, request):
        now = timezone.now()
        settle_expired_sessions(now)
        active = {session.table_id: session for session in Session.objects.filter(status='active')}
        tables = []
        from table.reservations import reservation_data
        for table in Table.objects.order_by('number'):
            session = active.get(table.id)
            tables.append({
                'id': table.id, 'number': table.number, 'type': table.table_type, 'reservations': reservation_data(table.id),
                'rate': str(table.price_per_hour),
                'start': session.start_time.isoformat() if session and session.start_time else None,
                'deadline': session.scheduled_end.isoformat() if session and session.scheduled_end else None,
                'billing_type': session.billing_type if session else None,
                'prepaid_amount': str(session.prepaid_amount) if session else '0',
                'session_id': session.id if session else None,
            })
        expired = Session.objects.filter(
            status='stopped', billing_type='prepaid', end_time=F('scheduled_end'),
            scheduled_end__gte=now - timedelta(hours=24), scheduled_end__lte=now,
        ).select_related('table').order_by('scheduled_end', 'pk')
        return JsonResponse({
            'success': True, 'tables': tables,
            'expired': [{
                'id': session.id,
                'table_number': session.table.number if session.table else None,
                'table_type': session.device_type,
                'device_name': session.device_name,
                'deadline': session.scheduled_end.isoformat(),
            } for session in expired],
        })


@method_decorator(staff_member_required, name='dispatch')
class LivePriceAPIView(View):
    def get(self, request, table_id):
        settle_expired_sessions()
        session = Session.objects.filter(table_id=table_id, status='active').first()
        if not session:
            return JsonResponse({'active': False})
        return JsonResponse({'active': True, 'price': session.calculate_total(live=True)})
