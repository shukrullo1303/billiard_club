import calendar
import csv
from datetime import datetime
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from session.models import Session
from table.models import BarSale, BarSaleItem, Table
from table.views import DashboardView


MONTH_NAMES = [
    '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
    'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr',
]


def _number(value, default, minimum, maximum):
    try:
        parsed = int(value)
        if minimum <= parsed <= maximum:
            return parsed, False
    except (TypeError, ValueError):
        pass
    return default, True


def _device_label(number, table_type):
    if number is None:
        return 'O‘chirilgan joy'
    if (table_type or '').lower() == 'playstation':
        return f'PS {number - 6 if number > 6 else number}'
    return f'{number}-stol'


class MonthlySelectView(DashboardView):
    template_name = 'monthly_select.html'

    def get_report_data(self):
        if hasattr(self, '_report_data'):
            return self._report_data

        today = timezone.localdate()
        year, invalid_year = _number(self.request.GET.get('year', today.year), today.year, 1900, 2100)
        month, invalid_month = _number(self.request.GET.get('month', today.month), today.month, 1, 12)
        tables = list(Table.objects.order_by('number'))
        table_value = self.request.GET.get('table', '')
        selected_table = next((table for table in tables if str(table.pk) == table_value), None)
        invalid_table = bool(table_value and selected_table is None)
        selected_table_id = selected_table.pk if selected_table else None
        selected_label = _device_label(selected_table.number, selected_table.table_type) if selected_table else 'Barcha stollar va PS'
        current_tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime(year, month, 1), current_tz)
        next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
        finish = timezone.make_aware(datetime(next_year, next_month, 1), current_tz)

        # New payments belong to the payment month, including active prepaid games.
        # Older records without paid_at retain their historical end-time attribution.
        paid_sessions = Session.objects.filter(payment_done=True).filter(
            Q(paid_at__isnull=False) | Q(status='stopped', end_time__isnull=False)
        ).annotate(revenue_date=Coalesce('paid_at', 'end_time'))
        sessions = paid_sessions.filter(revenue_date__gte=start, revenue_date__lt=finish)
        bar_sales = BarSale.objects.filter(payment_done=True, sold_at__gte=start, sold_at__lt=finish)
        if selected_table_id:
            sessions = sessions.filter(table_id=selected_table_id)
            bar_sales = bar_sales.filter(table_id=selected_table_id)

        is_ps = Q(device_type__iexact='PlayStation')
        summary = sessions.aggregate(
            billiard_total=Sum('total_price', filter=~is_ps), ps_total=Sum('total_price', filter=is_ps),
            billiard_count=Count('id', filter=~is_ps), ps_count=Count('id', filter=is_ps),
        )
        bar_summary = bar_sales.aggregate(total=Sum('total'), count=Count('id'))
        billiard_total = summary['billiard_total'] or Decimal('0')
        ps_total = summary['ps_total'] or Decimal('0')
        bar_total = bar_summary['total'] or Decimal('0')
        total = billiard_total + ps_total + bar_total
        game_count = summary['billiard_count'] + summary['ps_count']
        payment_count = game_count + bar_summary['count']
        daily = {}
        game_days = sessions.annotate(date=TruncDate('revenue_date')).values('date').annotate(
            billiard=Sum('total_price', filter=~is_ps), ps=Sum('total_price', filter=is_ps), count=Count('id'),
        )
        for row in game_days:
            daily[row['date']] = {
                'date': row['date'], 'billiard': row['billiard'] or Decimal('0'),
                'ps': row['ps'] or Decimal('0'), 'bar': Decimal('0'), 'count': row['count'],
            }
        for row in bar_sales.annotate(date=TruncDate('sold_at')).values('date').annotate(total=Sum('total'), count=Count('id')):
            day = daily.setdefault(row['date'], {'date': row['date'], 'billiard': Decimal('0'), 'ps': Decimal('0'), 'bar': Decimal('0'), 'count': 0})
            day['bar'] = row['total']
            day['count'] += row['count']
        daily_income = sorted(daily.values(), key=lambda row: row['date'], reverse=True)
        for day in daily_income:
            day['total'] = day['billiard'] + day['ps'] + day['bar']
        table_income = list(sessions.values('table__number', 'device_name', 'device_type').annotate(
            total=Sum('total_price'), count=Count('id'), average=Avg('total_price'),
        ).order_by('table__number'))
        for table in table_income:
            table['label'] = table['device_name'] or _device_label(table['table__number'], table['device_type'])
            table['kind'] = 'PlayStation' if (table['device_type'] or '').lower() == 'playstation' else 'Bilyard'
        bar_items = list(BarSaleItem.objects.filter(sale__in=bar_sales).values('name').annotate(
            quantity_sold=Sum('quantity'), total=Sum(F('quantity') * F('unit_price'), output_field=DecimalField(max_digits=14, decimal_places=2)),
        ).order_by('-total', 'name'))
        for item in bar_items:
            item['quantity'] = item['quantity_sold']
        years = {date.year for date in paid_sessions.datetimes('revenue_date', 'year')}
        years.update(date.year for date in BarSale.objects.filter(payment_done=True).datetimes('sold_at', 'year'))
        years.update((today.year, year))
        previous_year, previous_month = (year - 1, 12) if month == 1 else (year, month - 1)
        query = f'year={year}&month={month}'
        table_query = f'&table={selected_table_id}' if selected_table_id else ''
        base = reverse('reports:monthly_table')
        self._report_data = {
            'selected_year': year, 'selected_month': month, 'selected_table_id': selected_table_id,
            'selected_table': selected_table, 'selected_table_label': selected_label,
            'report_tables': [{'pk': table.pk, 'label': _device_label(table.number, table.table_type)} for table in tables],
            'month_name': MONTH_NAMES[month], 'month_list': [(number, MONTH_NAMES[number]) for number in range(1, 13)],
            'years_with_data': sorted(years, reverse=True), 'daily_income': daily_income,
            'table_income': table_income, 'bar_items': bar_items,
            'monthly_total': total, 'billiard_total': billiard_total, 'ps_total': ps_total, 'bar_total': bar_total,
            'billiard_count': summary['billiard_count'], 'ps_count': summary['ps_count'], 'bar_count': bar_summary['count'],
            'session_count': game_count, 'payment_count': payment_count,
            'average_payment': total / payment_count if payment_count else Decimal('0'),
            'report_sessions': sessions, 'report_bar_sales': bar_sales,
            'report_date_start': start.date(), 'report_date_end': start.date().replace(day=calendar.monthrange(year, month)[1]),
            'generated_at': timezone.localtime(),
            'filter_notice': 'Noto‘g‘ri filtr qiymati almashtirildi. Quyidagi yil, oy va stolni tekshiring.' if invalid_year or invalid_month or invalid_table else '',
            'previous_month_url': f'{base}?year={previous_year}&month={previous_month}{table_query}' if previous_year >= 1900 else '',
            'next_month_url': f'{base}?year={next_year}&month={next_month}{table_query}' if next_year <= 2100 else '',
            'current_month_url': f'{base}?year={today.year}&month={today.month}{table_query}',
            'export_url': f'{base}?{query}{table_query}&export=csv',
            'pdf_url': f'{base}?{query}{table_query}&format=pdf',
        }
        return self._report_data

    def get(self, request, *args, **kwargs):
        export_format = request.GET.get('format') or request.GET.get('export')
        if export_format in ('pdf', 'csv'):
            data = self.get_report_data()
            filename = f'hisobot-{data["selected_year"]}-{data["selected_month"]:02d}'
            if data['selected_table_id']:
                filename += f'-stol-{data["selected_table"].number}'
            if export_format == 'pdf':
                from weasyprint import HTML
                document = render_to_string('monthly_pdf.html', data, request=request)
                response = HttpResponse(HTML(string=document).write_pdf(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                return response
            response = HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
            response.write('\ufeff')
            writer = csv.writer(response)
            writer.writerow(['To‘lov sanasi', 'Bo‘lim', 'Stol / PS', 'Tafsilot', 'To‘langan summa (so‘m)'])
            records = []
            for session in data['report_sessions'].select_related('table'):
                moment = timezone.localtime(session.revenue_date)
                records.append((moment, 'PlayStation' if session.device_type.lower() == 'playstation' else 'Bilyard',
                                session.device_name or (_device_label(session.table.number, session.table.table_type) if session.table else 'O‘chirilgan joy'),
                                'Oldindan to‘lov' if session.billing_type == 'prepaid' else 'O‘yin to‘lovi', session.total_price))
            for sale in data['report_bar_sales'].select_related('table').prefetch_related('items'):
                description = ', '.join(f'{item.name} x {item.quantity}' for item in sale.items.all())
                # Keep product names from becoming spreadsheet formulas.
                if description.lstrip().startswith(('=', '+', '-', '@')):
                    description = "'" + description
                records.append((timezone.localtime(sale.sold_at), 'Bar',
                                _device_label(sale.table.number, sale.table.table_type) if sale.table else 'Bar / kassa',
                                description, sale.total))
            for moment, category, label, description, amount in sorted(records, key=lambda row: row[0]):
                writer.writerow([moment.strftime('%d.%m.%Y %H:%M'), category, label, description, format(amount, '.2f')])
            return response
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_report_data())
        return context


class MonthlyTableView(MonthlySelectView):
    template_name = 'monthly_table.html'
