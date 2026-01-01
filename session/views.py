from django.views import View
from django.http import JsonResponse
from django.utils import timezone
from table.models import Table
from session.models import Session

class StartSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        session = Session.objects.create(table=table, start_time=timezone.now(), status='active')
        table.start_session()
        return JsonResponse({'success': True, 'start_time': session.start_time.isoformat()})

class StopSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        session = table.sessions.filter(status='active').first()
        if session:
            session.end_time = timezone.now()
            session.status = 'waiting_payment'
            session.total_price = session.calculate_price()
            session.save()
            table.stop_session()
            return JsonResponse({
                'success': True,
                'session': {
                    'id': session.id,
                    'table_number': table.number,
                    'price': session.total_price
                }
            })
        else:
            return JsonResponse({'success': False, 'error': 'No active session found.'})
