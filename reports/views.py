from django.views.generic import TemplateView
from session.models import Session
from django.db.models import Sum
from django.db.models.functions import TruncDate
from calendar import month_name


class MonthlySelectView(TemplateView):
    template_name = 'monthly_select.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sessions = Session.objects.filter(payment_done=True)
        months_with_data = sorted({(s.end_time.year, s.end_time.month) for s in sessions}, reverse=True)
        years_with_data = sorted({s.end_time.year for s in sessions}, reverse=True)

        selected_year = int(self.request.GET.get('year', years_with_data[0] if years_with_data else 2025))

        # Faqat tanlangan yil uchun oylar
        months_for_selected_year = [m for y,m in months_with_data if y == selected_year]

        context.update({
            'years_with_data': years_with_data,
            'month_list': [(i, month_name[i]) for i in range(1, 13)],
            'months_for_selected_year': months_for_selected_year,
            'selected_year': selected_year,
            'selected_month': int(self.request.GET.get('month', months_for_selected_year[0] if months_for_selected_year else 1)),
        })
        return context



class MonthlyTableView(TemplateView):
    template_name = 'monthly_table.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        year = int(self.request.GET.get('year', kwargs.get('year', 2025)))
        month = int(self.request.GET.get('month', kwargs.get('month', 1)))

        sessions = Session.objects.filter(payment_done=True, end_time__year=year, end_time__month=month)
        daily_income = sessions.annotate(date=TruncDate('end_time')).values('date').annotate(total=Sum('total_price')).order_by('date')
        monthly_total = sessions.aggregate(total=Sum('total_price'))['total'] or 0

        context.update({
            'daily_income': daily_income,
            'monthly_total': monthly_total,
            'selected_year': year,
            'selected_month': month,
            'month_name': month_name[month],
        })
        return context
