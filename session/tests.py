import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from table.models import Table
from .models import Session, settle_expired_sessions


class SessionBillingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('session-admin', 'session@example.com', 'password')
        self.client.force_login(self.user)
        self.table = Table.objects.get(number=1)
        self.table.price_per_hour = 50000
        self.table.save(update_fields=['price_per_hour'])
        self.now = timezone.make_aware(datetime(2026, 10, 6, 14, 0))

    def start(self, data=None, table=None, at=None):
        with patch('django.utils.timezone.now', return_value=at or self.now):
            return self.client.post(f'/start/{(table or self.table).id}/', json.dumps(data or {}), content_type='application/json')

    def test_metered_session_rounds_up_to_thousand_and_pays_once(self):
        response = self.start()
        self.assertEqual(response.status_code, 200)
        session = Session.objects.get(pk=response.json()['session_id'])
        self.assertIsNone(session.paid_at)
        self.assertFalse(session.payment_done)
        self.assertEqual(self.start().status_code, 409)
        self.assertEqual(self.client.post(f'/payment/{session.id}/').status_code, 409)
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(minutes=31)):
            stop = self.client.post(f'/stop/{self.table.id}/')
            self.assertEqual(stop.status_code, 200)
            self.assertEqual(Decimal(stop.json()['session']['price']), Decimal('26000'))
            self.assertEqual(self.client.post(f'/stop/{self.table.id}/').status_code, 409)
            self.assertEqual(self.client.post(f'/payment/{session.id}/').status_code, 200)
            self.assertEqual(self.client.post(f'/payment/{session.id}/').status_code, 409)
        session.refresh_from_db()
        self.assertEqual(session.paid_at, self.now + timedelta(minutes=31))

    def test_30_minutes_is_paid_immediately_and_ends_at_deadline(self):
        response = self.start({'mode': 'prepaid', 'prepaid_minutes': 30})
        self.assertEqual(response.status_code, 200)
        session = Session.objects.get(pk=response.json()['session_id'])
        self.assertTrue(session.payment_done)
        self.assertEqual(session.paid_at, self.now)
        self.assertEqual(session.total_price, Decimal('25000'))
        self.assertEqual(session.scheduled_end, self.now + timedelta(minutes=30))
        self.assertEqual(settle_expired_sessions(self.now + timedelta(minutes=29, seconds=59)), [])
        self.assertEqual(len(settle_expired_sessions(self.now + timedelta(hours=8))), 1)
        session.refresh_from_db()
        self.table.refresh_from_db()
        self.assertEqual(session.end_time, self.now + timedelta(minutes=30))
        self.assertEqual(session.status, 'stopped')
        self.assertEqual(session.total_price, Decimal('25000'))
        self.assertEqual(session.paid_at, self.now)
        self.assertFalse(self.table.is_active)
        self.assertEqual(settle_expired_sessions(self.now + timedelta(hours=9)), [])
        self.assertEqual(self.client.post(f'/payment/{session.id}/').status_code, 409)

    def test_prepaid_amount_sets_exact_duration_and_early_stop_keeps_payment(self):
        response = self.start({'mode': 'prepaid', 'prepaid_amount': '12500'})
        session = Session.objects.get(pk=response.json()['session_id'])
        self.assertEqual(session.scheduled_end, self.now + timedelta(minutes=15))
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(minutes=3)):
            response = self.client.post(f'/stop/{self.table.id}/')
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.total_price, Decimal('12500'))
        self.assertTrue(session.payment_done)
        self.assertEqual(session.paid_at, self.now)
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(hours=1)):
            self.assertEqual(self.client.get('/state/').json()['expired'], [])

    def test_state_settles_at_deadline_and_keeps_notifications_after_reload(self):
        response = self.start({'mode': 'prepaid', 'prepaid_minutes': 60})
        session_id = response.json()['session_id']
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(minutes=60)):
            first = self.client.get('/state/').json()
            second = self.client.get('/state/').json()
        state = next(t for t in first['tables'] if t['id'] == self.table.id)
        self.assertIsNone(state['start'])
        self.assertIsNone(state['deadline'])
        self.assertEqual(first['expired'][0]['id'], session_id)
        self.assertEqual(first['expired'], second['expired'])
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(hours=26)):
            self.assertEqual(self.client.get('/state/').json()['expired'], [])

    def test_playstation_has_independent_prepaid_session(self):
        ps = Table.objects.get(number=7)
        self.assertEqual(ps.table_type, 'PlayStation')
        self.assertEqual(ps.price_per_hour, Decimal('30000'))
        self.assertEqual(Table.objects.get(number=8).table_type, 'PlayStation')
        response = self.start({'mode': 'prepaid', 'prepaid_minutes': 60}, table=ps)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()['prepaid_amount']), Decimal('30000'))
        with patch('django.utils.timezone.now', return_value=self.now + timedelta(minutes=10)):
            state = self.client.get('/state/').json()
        row = next(t for t in state['tables'] if t['id'] == ps.id)
        self.assertEqual(row['type'], 'PlayStation')
        self.assertEqual(row['billing_type'], 'prepaid')
        self.assertEqual(datetime.fromisoformat(row['deadline']), self.now + timedelta(hours=1))
        self.assertFalse(self.table.sessions.exists())

    def test_expired_table_can_start_another_game(self):
        first = self.start({'mode': 'prepaid', 'prepaid_minutes': 30})
        second = self.start(at=self.now + timedelta(minutes=31))
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()['session_id'], second.json()['session_id'])
        self.assertEqual(self.table.sessions.filter(status='active').count(), 1)

    def test_prepaid_minutes_round_up_to_whole_som(self):
        self.table.price_per_hour = 50001
        self.table.save(update_fields=['price_per_hour'])
        response = self.start({'mode': 'prepaid', 'prepaid_minutes': 30})
        self.assertEqual(Decimal(response.json()['prepaid_amount']), Decimal('25001'))

    def test_invalid_options_do_not_create_or_activate_a_game(self):
        invalid = [
            {'mode': 'bad'}, {'mode': 'prepaid'},
            {'mode': 'prepaid', 'prepaid_minutes': 45},
            {'mode': 'prepaid', 'prepaid_minutes': True},
            {'mode': 'prepaid', 'prepaid_minutes': 30, 'prepaid_amount': 1000},
            {'mode': 'prepaid', 'prepaid_amount': 0},
            {'mode': 'prepaid', 'prepaid_amount': -1},
            {'mode': 'prepaid', 'prepaid_amount': 'NaN'},
            {'mode': 'prepaid', 'prepaid_amount': 'Infinity'},
            {'mode': 'prepaid', 'prepaid_amount': '1.5'},
            {'mode': 'prepaid', 'prepaid_amount': True},
            {'mode': 'prepaid', 'prepaid_amount': '10000000000'},
            ['not', 'an', 'object'],
        ]
        for data in invalid:
            with self.subTest(data=data):
                self.assertEqual(self.start(data).status_code, 400)
        self.assertFalse(Session.objects.exists())
        self.table.refresh_from_db()
        self.assertFalse(self.table.is_active)
        self.assertEqual(self.client.post(f'/start/{self.table.id}/', '{', content_type='application/json').status_code, 400)

    def test_zero_rate_rejected_and_empty_legacy_request_still_works(self):
        self.table.price_per_hour = 0
        self.table.save(update_fields=['price_per_hour'])
        self.assertEqual(self.start().status_code, 400)
        self.assertEqual(self.start({'mode': 'prepaid', 'prepaid_amount': 1000}).status_code, 400)
        self.table.price_per_hour = 50000
        self.table.save(update_fields=['price_per_hour'])
        self.assertEqual(self.client.post(f'/start/{self.table.id}/').status_code, 200)

    def test_deleting_table_keeps_session_history(self):
        response = self.start({'mode': 'prepaid', 'prepaid_minutes': 30})
        self.table.delete()
        session = Session.objects.get(pk=response.json()['session_id'])
        self.assertIsNone(session.table)
        self.assertEqual(session.device_name, '1-stol')
        self.assertIn('1-stol', str(session))
        self.assertEqual(len(settle_expired_sessions(self.now + timedelta(hours=1))), 1)

    def test_anonymous_cannot_read_or_modify_sessions(self):
        self.client.logout()
        self.assertEqual(self.client.get('/state/').status_code, 302)
        self.assertEqual(self.start().status_code, 302)
