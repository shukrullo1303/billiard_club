# session/views.py
from django.http import JsonResponse
from session.models import Session
from django.utils import timezone
from django.db.models import Sum

def payment_view(request, session_id):
    if request.method == 'POST':
        session = Session.objects.get(id=session_id)
        session.payment_done = True
        session.save(update_fields=['payment_done'])

        # Bugungi jami foyda
        today = timezone.localdate()
        total_income = Session.objects.filter(
            payment_done=True,
            end_time__date=today
        ).aggregate(total=Sum('total_price'))['total'] or 0

        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'total_income': total_income
        })
    return JsonResponse({'success': False, 'error': 'Invalid request'})
