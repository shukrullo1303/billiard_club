from django.views.generic import TemplateView, View
from table.models import Table
from session.models import Session
from django.utils import timezone
from session.models import Session
from django.db.models import Prefetch
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator


@method_decorator(staff_member_required, name='dispatch')
class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tables_data = []

        for table in Table.objects.prefetch_related('sessions').all():
            active_session = table.sessions.filter(status='active').first()
            tables_data.append({
                'id': table.id,
                'number': table.number,
                'price_per_hour': float(table.price_per_hour),
                'active_session': {
                    'id': active_session.id,
                    'start_time': active_session.start_time,
                    'end_time': active_session.end_time,
                    'total_price': active_session.total_price
                } if active_session else None
            })

        today = timezone.localdate()
        context['tables'] = tables_data
        context['paid_sessions'] = Session.objects.filter(
            payment_done=True,
            end_time__date=today
        ).order_by('end_time')
        context['unpaid_sessions'] = Session.objects.filter(payment_done=False).order_by('start_time')
        context['total_income'] = sum([s.total_price for s in context['paid_sessions']])
        return context
