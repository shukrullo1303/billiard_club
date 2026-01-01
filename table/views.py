from django.views.generic import TemplateView
from table.models import Table
from session.models import Session
from django.utils import timezone
from django.db.models import Sum

class TableDashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tables = Table.objects.all()
        # Paid sessions for today
        today = timezone.localdate()
        paid_sessions = Session.objects.filter(
            payment__isnull=False,
            end_time__date=today
        )
        total_income = paid_sessions.aggregate(total=Sum('total_price'))['total'] or 0

        context.update({
            "tables": tables,
            "paid_sessions": paid_sessions,
            "total_income": total_income,
        })
        return context
