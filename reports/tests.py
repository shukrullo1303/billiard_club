import csv
import io
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from session.models import Session
from table.models import BarSale, BarSaleItem, Table


class MonthlyReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('report-admin', 'report@example.com', 'password')
        self.client.force_login(self.user)
        self.table_one, _ = Table.objects.get_or_create(number=1, defaults={'price_per_hour': 50000})
        self.table_two, _ = Table.objects.get_or_create(number=2, defaults={'price_per_hour': 60000})

    def add_session(self, day=2, amount='20000.00', table=None, paid=True, status='stopped', end=None):
        end = end or timezone.make_aware(datetime(2026, 10, day, 16, 0))
        return Session.objects.create(
            table=table or self.table_one, start_time=end - timedelta(hours=1),
            end_time=end, total_price=Decimal(amount), payment_done=paid, status=status,
        )

    def test_default_report_opens_current_month_with_controls_and_empty_state(self):
        response = self.client.get(reverse('reports:monthly_select'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_month'], timezone.localdate().month)
        self.assertEqual(response.context['selected_year'], timezone.localdate().year)
        self.assertContains(response, 'Bu davrda to‘lovlar yo‘q')
        self.assertContains(response, 'id="bar-nav"')
        self.assertContains(response, 'id="control-drawer"')
        self.assertEqual(response.context['monthly_total'], 0)
        self.assertEqual(response.context['average_payment'], 0)

    def test_daily_and_table_totals_include_only_paid_finished_sessions(self):
        self.add_session(amount='20000.00')
        self.add_session(amount='40000.00', table=self.table_two)
        self.add_session(day=3, amount='30000.00')
        self.add_session(amount='900000.00', paid=False)
        self.add_session(amount='700000.00', status='active')
        self.add_session(end=timezone.make_aware(datetime(2026, 9, 30, 23, 59)), amount='600000.00')
        response = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['monthly_total'], Decimal('90000'))
        self.assertEqual(response.context['session_count'], 3)
        self.assertEqual(response.context['average_payment'], Decimal('30000'))
        days = response.context['daily_income']
        self.assertEqual([day['date'].day for day in days], [3, 2])
        self.assertEqual([day['total'] for day in days], [Decimal('30000'), Decimal('60000')])
        self.assertEqual([row['total'] for row in response.context['table_income']], [Decimal('50000'), Decimal('40000')])

    def test_table_filter_applies_to_summary_breakdowns_and_export(self):
        self.add_session(amount='20000.00')
        self.add_session(amount='40000.00', table=self.table_two)
        query = {'year': 2026, 'month': 10, 'table': self.table_two.pk}
        response = self.client.get(reverse('reports:monthly_table'), query)
        self.assertEqual(response.context['monthly_total'], Decimal('40000'))
        self.assertEqual(response.context['session_count'], 1)
        self.assertEqual(response.context['selected_table_id'], self.table_two.pk)
        self.assertEqual(len(response.context['table_income']), 1)
        self.assertIn(f'table={self.table_two.pk}', response.context['previous_month_url'])
        query['export'] = 'csv'
        exported = self.client.get(reverse('reports:monthly_table'), query)
        self.assertEqual(exported.status_code, 200)
        self.assertIn('text/csv', exported['Content-Type'])
        self.assertIn('hisobot-2026-10-stol-2.csv', exported['Content-Disposition'])
        rows = list(csv.reader(io.StringIO(exported.content.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][2], '2-stol')
        self.assertEqual(rows[1][4], '40000.00')

    def test_month_boundary_uses_local_timezone(self):
        self.add_session(end=timezone.make_aware(datetime(2026, 10, 1, 0, 0)), amount='15000')
        self.add_session(end=timezone.make_aware(datetime(2026, 10, 31, 23, 59)), amount='25000')
        self.add_session(end=timezone.make_aware(datetime(2026, 11, 1, 0, 0)), amount='99999')
        response = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 10})
        self.assertEqual(response.context['monthly_total'], Decimal('40000'))
        self.assertEqual({day['date'].day for day in response.context['daily_income']}, {1, 31})

    def test_invalid_filters_fall_back_with_notice_without_server_error(self):
        for query in (
            {'year': 'wrong', 'month': '0', 'table': 'missing'},
            {'year': '99999', 'month': '13'},
            {'year': '', 'month': '-1'},
        ):
            with self.subTest(query=query):
                response = self.client.get(reverse('reports:monthly_table'), query)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context['selected_year'], timezone.localdate().year)
                self.assertEqual(response.context['selected_month'], timezone.localdate().month)
                self.assertContains(response, 'Noto‘g‘ri filtr qiymati almashtirildi')

    def test_previous_and_next_month_cross_year_boundary(self):
        january = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 1})
        self.assertIn('year=2025&month=12', january.context['previous_month_url'])
        december = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 12})
        self.assertIn('year=2027&month=1', december.context['next_month_url'])

    def test_anonymous_cannot_read_report_or_export(self):
        self.client.logout()
        for query in ({}, {'export': 'csv'}, {'format': 'pdf'}):
            response = self.client.get(reverse('reports:monthly_table'), query)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/admin/login/', response.url)

    def test_paid_active_prepaid_and_bar_have_separate_revenue(self):
        moment = timezone.make_aware(datetime(2026, 10, 8, 14, 0))
        ps = Table.objects.get(number=7)
        Session.objects.create(table=ps, start_time=moment, scheduled_end=moment + timedelta(hours=1),
                               paid_at=moment, billing_type='prepaid', prepaid_amount=30000,
                               total_price=30000, status='active', payment_done=True)
        self.add_session(day=8, amount='50000')
        sale = BarSale.objects.create(sold_at=moment, total=24000, request_key=uuid.uuid4())
        BarSaleItem.objects.create(sale=sale, name='Coca-Cola', quantity=2, unit_price=12000)
        response = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 10})
        self.assertEqual(response.context['monthly_total'], Decimal('104000'))
        self.assertEqual(response.context['billiard_total'], Decimal('50000'))
        self.assertEqual(response.context['ps_total'], Decimal('30000'))
        self.assertEqual(response.context['bar_total'], Decimal('24000'))
        self.assertEqual(response.context['payment_count'], 3)
        self.assertEqual(response.context['bar_items'][0]['quantity'], 2)
        self.assertEqual(response.context['daily_income'][0]['total'], Decimal('104000'))
        self.assertContains(response, 'PS 1')
        self.assertContains(response, 'PDF yuklash')

    def test_actual_payment_date_takes_precedence_over_game_end(self):
        session = self.add_session(end=timezone.make_aware(datetime(2026, 9, 30, 23, 30)), amount='55000')
        session.paid_at = timezone.make_aware(datetime(2026, 10, 1, 0, 5))
        session.save(update_fields=['paid_at'])
        october = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 10})
        september = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 9})
        self.assertEqual(october.context['monthly_total'], Decimal('55000'))
        self.assertEqual(september.context['monthly_total'], 0)

    def test_bar_filter_and_csv_use_sale_snapshot(self):
        moment = timezone.make_aware(datetime(2026, 10, 8, 14, 0))
        included = BarSale.objects.create(sold_at=moment, table=self.table_two, total=14000, request_key=uuid.uuid4())
        BarSaleItem.objects.create(sale=included, name='=SUM(A1)', quantity=2, unit_price=7000)
        BarSale.objects.create(sold_at=moment, table=self.table_one, total=99999, request_key=uuid.uuid4())
        query = {'year': 2026, 'month': 10, 'table': self.table_two.pk}
        response = self.client.get(reverse('reports:monthly_table'), query)
        self.assertEqual(response.context['bar_total'], Decimal('14000'))
        self.assertEqual(response.context['bar_items'][0]['total'], Decimal('14000'))
        query['export'] = 'csv'
        exported = self.client.get(reverse('reports:monthly_table'), query)
        rows = list(csv.reader(io.StringIO(exported.content.decode('utf-8-sig'))))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][1], 'Bar')
        self.assertTrue(rows[1][3].startswith("'="))

    def test_pdf_export_returns_a_real_download(self):
        self.add_session(amount='45000')
        response = self.client.get(reverse('reports:monthly_table'), {'year': 2026, 'month': 10, 'format': 'pdf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('hisobot-2026-10.pdf', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreater(len(response.content), 5000)

    def test_deleted_playstation_keeps_historical_classification_and_export_name(self):
        ps = Table.objects.get(number=7)
        self.add_session(table=ps, amount='35000')
        ps.delete()
        query = {'year': 2026, 'month': 10}
        response = self.client.get(reverse('reports:monthly_table'), query)
        self.assertEqual(response.context['ps_total'], Decimal('35000'))
        self.assertEqual(response.context['billiard_total'], 0)
        self.assertEqual(response.context['table_income'][0]['label'], 'PS 1')
        query['export'] = 'csv'
        exported = self.client.get(reverse('reports:monthly_table'), query)
        rows = list(csv.reader(io.StringIO(exported.content.decode('utf-8-sig'))))
        self.assertEqual(rows[1][1:3], ['PlayStation', 'PS 1'])
