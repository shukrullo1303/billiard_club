import json
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from .models import Reservation, Table


def reservation_data(table_id):
    return [{'id': r.id, 'customer': r.customer, 'note': r.note, 'starts_at': r.starts_at.isoformat()} for r in Reservation.objects.filter(table_id=table_id, active=True)]


@method_decorator(staff_member_required, name='dispatch')
class ReservationView(View):
    @transaction.atomic
    def post(self, request, table_id):
        table = get_object_or_404(Table.objects.select_for_update(), pk=table_id)
        try:
            data = json.loads(request.body)
            if data.get('cancel'):
                reservation = get_object_or_404(Reservation, table=table, pk=data['cancel'], active=True)
                reservation.active = False
                reservation.save(update_fields=['active'])
            else:
                customer = str(data.get('customer', '')).strip()
                note = str(data.get('note', '')).strip()
                starts = parse_datetime(str(data.get('starts_at', '')))
                if starts and timezone.is_naive(starts):
                    starts = timezone.make_aware(starts)
                if len(customer) > 100 or len(note) > 300 or not starts or starts <= timezone.now():
                    raise ValueError('Izohni tekshiring va kelajakdagi bron vaqtini kiriting.')
                if Reservation.objects.filter(table=table, starts_at=starts, active=True).exists():
                    raise ValueError('Bu vaqtga bron mavjud.')
                Reservation.objects.create(table=table, customer=customer, note=note, starts_at=starts)
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            return JsonResponse({'error': str(error) or 'Bron ma’lumotlarini tekshiring.'}, status=400)
        return JsonResponse({'success': True, 'reservations': reservation_data(table_id)})
