from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.utils import timezone
from table.models import Table
from .models import Session

class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tables'] = Table.objects.all().prefetch_related('sessions')
        
        today = timezone.now().date()
        paid_sessions = Session.objects.filter(payment_done=True, end_time__date=today).order_by('end_time')
        context['paid_sessions'] = paid_sessions
        context['total_income'] = sum([s.total_price for s in paid_sessions])
        return context


class StartSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        table.is_active = True
        table.save()

        session = Session.objects.create(
            table=table,
            start_time=timezone.now(),
            status="active"
        )
        return JsonResponse({"success": True, "start_time": session.start_time.isoformat(), "session_id": session.id})


class StopSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        table.is_active = False
        table.save()

        session = table.sessions.filter(status="active").last()
        if session:
            session.end_time = timezone.now()
            session.status = "stopped"
            session.calculate_total()

        return JsonResponse({
            "success": True,
            "session": {
                "id": session.id,
                "table_number": table.number,
                "price": session.total_price
            }
        })


class PaySessionView(View):
    def post(self, request, session_id):
        session = Session.objects.get(id=session_id)
        session.payment_done = True
        session.save()

        # Bugungi jami foyda
        today = timezone.now().date()
        total_income = sum([s.total_price for s in Session.objects.filter(payment_done=True, end_time__date=today)])
        
        return JsonResponse({"success": True, "total_income": total_income})
