import json
import tempfile
import uuid
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from table.models import Table, BarProduct, BarSale, BarSaleItem
from session.models import Session


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('test-admin', 'test@example.com', 'password')
        self.client.force_login(self.user)

    def test_initial_layout_and_dashboard(self):
        self.assertEqual(Table.objects.get(number=1).position_x, 19)
        self.assertEqual(Table.objects.get(number=4).rotation, 270)
        response = self.client.get('/')
        self.assertContains(response, 'Zal xaritasi')
        self.assertContains(response, 'Bar mahsulotlari')

    def test_layout_persists_and_rejects_invalid_batch(self):
        rows = [{'id': t.id, 'x': t.position_x, 'y': t.position_y, 'rotation': t.rotation} for t in Table.objects.all()]
        rows[0]['rotation'] = 270
        self.assertEqual(self.client.post('/layout/save/', json.dumps({'tables': rows}), content_type='application/json').status_code, 200)
        self.assertEqual(Table.objects.get(pk=rows[0]['id']).rotation, 270)
        rows[0]['rotation'] = 45
        self.assertEqual(self.client.post('/layout/save/', json.dumps({'tables': rows}), content_type='application/json').status_code, 400)
        self.assertEqual(Table.objects.get(pk=rows[0]['id']).rotation, 270)

    def test_product_create_edit_validation(self):
        data = {'name': 'Choy', 'category': 'Ichimliklar', 'price': 5000, 'stock': 10}
        self.assertEqual(self.client.post('/bar/save/', json.dumps(data), content_type='application/json').status_code, 200)
        data.update(id=BarProduct.objects.get().id, stock=8)
        self.client.post('/bar/save/', json.dumps(data), content_type='application/json')
        self.assertEqual(BarProduct.objects.get().stock, 8)
        data['price'] = -1
        self.assertEqual(self.client.post('/bar/save/', json.dumps(data), content_type='application/json').status_code, 400)
        self.assertEqual(BarProduct.objects.get().price, 5000)

    def test_session_lifecycle_and_duplicate_actions(self):
        t = Table.objects.first()
        self.assertEqual(self.client.post(f'/stop/{t.id}/').status_code, 409)
        self.assertEqual(self.client.post(f'/start/{t.id}/').status_code, 200)
        self.assertEqual(self.client.post(f'/start/{t.id}/').status_code, 409)
        s = Session.objects.get(table=t)
        self.assertEqual(self.client.post(f'/payment/{s.id}/').status_code, 409)
        self.assertEqual(self.client.post(f'/stop/{t.id}/').status_code, 200)
        self.assertEqual(self.client.post(f'/payment/{s.id}/').status_code, 200)
        self.assertEqual(self.client.post(f'/payment/{s.id}/').status_code, 409)
        s.refresh_from_db()
        self.assertTrue(s.payment_done)

    def test_anonymous_cannot_modify(self):
        self.client.logout()
        self.assertEqual(self.client.post('/layout/save/', '{}', content_type='application/json').status_code, 302)
        self.assertEqual(self.client.post('/bar/save/', '{}', content_type='application/json').status_code, 302)


class ProductImageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('image-admin', 'image@example.com', 'password')
        self.client.force_login(self.user)
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.media_override = self.settings(MEDIA_ROOT=self.media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)

    def upload(self, image_format='PNG'):
        buffer = BytesIO()
        Image.new('RGB', (1500, 600), '#117755').save(buffer, format=image_format)
        return SimpleUploadedFile(f'original.{image_format.lower()}', buffer.getvalue(), content_type=f'image/{image_format.lower()}')

    def product_data(self, **updates):
        return dict(name='Limonad', category='Ichimliklar', price='12000', stock='15', **updates)

    def test_image_is_optional(self):
        response = self.client.post('/bar/save/', self.product_data())
        self.assertEqual(response.status_code, 200)
        product = BarProduct.objects.get(pk=response.json()['product']['id'])
        self.assertFalse(product.image)
        self.assertEqual(response.json()['product']['image_url'], '')
        self.assertEqual(list(Path(self.media.name).rglob('*')), [])

    def test_jpeg_and_png_are_resized_and_reencoded_as_webp(self):
        for image_format in ('JPEG', 'PNG'):
            with self.subTest(image_format=image_format):
                response = self.client.post('/bar/save/', self.product_data(image=self.upload(image_format)))
                self.assertEqual(response.status_code, 200)
                product = BarProduct.objects.get(pk=response.json()['product']['id'])
                self.assertTrue(product.image.name.endswith('.webp'))
                self.assertNotIn('original', product.image.name)
                with Image.open(product.image.path) as saved:
                    self.assertEqual(saved.format, 'WEBP')
                    self.assertEqual(saved.size, (1200, 480))
                    self.assertEqual(saved.mode, 'RGB')
                image_response = self.client.get(response.json()['product']['image_url'])
                self.assertEqual(image_response.status_code, 200)
                self.assertEqual(image_response['Content-Type'], 'image/webp')
                self.assertTrue(b''.join(image_response.streaming_content).startswith(b'RIFF'))
                image_response.close()

    def test_edit_preserves_image_until_explicitly_removed(self):
        response = self.client.post('/bar/save/', self.product_data(image=self.upload()))
        product = BarProduct.objects.get(pk=response.json()['product']['id'])
        original_name, original_path = product.image.name, Path(product.image.path)
        data = self.product_data(id=product.id)
        data['stock'] = '9'
        response = self.client.post('/bar/save/', data)
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.stock, 9)
        self.assertEqual(product.image.name, original_name)
        self.assertTrue(original_path.exists())

        response = self.client.post('/bar/save/', dict(data, remove_image='true'))
        self.assertEqual(response.status_code, 200)
        product.refresh_from_db()
        self.assertFalse(product.image)
        self.assertFalse(original_path.exists())
        self.assertEqual(response.json()['product']['image_url'], '')
        self.assertEqual(self.client.get(f'/bar/image/{product.id}/').status_code, 404)

    def test_invalid_upload_does_not_change_product_or_existing_image(self):
        response = self.client.post('/bar/save/', self.product_data(image=self.upload()))
        product = BarProduct.objects.get(pk=response.json()['product']['id'])
        original_name = product.image.name
        original_bytes = Path(product.image.path).read_bytes()
        gif = BytesIO()
        Image.new('RGB', (10, 10)).save(gif, format='GIF')
        invalid_uploads = [
            SimpleUploadedFile('fake.png', b'not an image', content_type='image/png'),
            SimpleUploadedFile('unsupported.gif', gif.getvalue(), content_type='image/gif'),
            SimpleUploadedFile('large.png', b'x' * (5 * 1024 * 1024 + 1), content_type='image/png'),
        ]
        for upload in invalid_uploads:
            with self.subTest(filename=upload.name):
                data = self.product_data(id=product.id, image=upload, remove_image='true')
                data.update(name='Changed', price='1', stock='0')
                self.assertEqual(self.client.post('/bar/save/', data).status_code, 400)
                product.refresh_from_db()
                self.assertEqual((product.name, product.price, product.stock), ('Limonad', Decimal('12000'), 15))
                self.assertEqual(product.image.name, original_name)
                self.assertEqual(Path(product.image.path).read_bytes(), original_bytes)
                self.assertEqual(BarProduct.objects.count(), 1)
                self.assertEqual(len(list(Path(self.media.name).rglob('*.webp'))), 1)


class BarSaleTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('sale-admin', 'sale@example.com', 'password')
        self.client.force_login(self.user)
        self.water = BarProduct.objects.create(name='A suv', category='Bar', price=5000, stock=10)
        self.snack = BarProduct.objects.create(name='Z chips', category='Bar', price=12000, stock=2)

    def sell(self, items, **updates):
        data = {'request_key': str(uuid.uuid4()), 'items': items}
        data.update(updates)
        return self.client.post('/bar/sale/', json.dumps(data), content_type='application/json')

    def test_sale_reduces_stock_and_preserves_receipt_snapshots(self):
        table = Table.objects.get(number=1)
        response = self.sell([{'id': self.water.id, 'quantity': 3}, {'id': self.snack.id, 'quantity': 2}], table_id=table.id)
        self.assertEqual(response.status_code, 200)
        sale = BarSale.objects.get(pk=response.json()['sale_id'])
        self.assertEqual(sale.total, Decimal('39000'))
        self.assertEqual(sale.table, table)
        self.water.refresh_from_db()
        self.snack.refresh_from_db()
        self.assertEqual((self.water.stock, self.snack.stock), (7, 0))
        item = sale.items.get(product=self.water)
        self.assertEqual((item.name, item.unit_price, item.quantity), ('A suv', Decimal('5000'), 3))

        self.water.name, self.water.price = 'Yangi suv', 10000
        self.water.save()
        item.refresh_from_db()
        self.assertEqual((item.name, item.unit_price), ('A suv', Decimal('5000')))
        self.snack.delete()
        self.assertEqual(sale.items.get(name='Z chips').product_id, None)
        sale.refresh_from_db()
        self.assertEqual(sale.total, Decimal('39000'))

    def test_saved_order_is_pending_until_paid_and_counted_once(self):
        from django.utils import timezone
        device = Table.objects.get(number=1)
        session = Session.objects.create(table=device, start_time=timezone.now(), status='active')
        result = self.sell([{'id': self.water.id, 'quantity': 2}], table_id=device.id, session_id=session.id, defer_payment=True)
        self.assertEqual(result.status_code, 200)
        sale = BarSale.objects.get(pk=result.json()['sale_id'])
        self.assertFalse(sale.payment_done)
        self.assertEqual(sale.session_id, session.id)
        report = self.client.get('/reports/')
        self.assertEqual(report.context['bar_total'], 0)
        self.assertTrue(any(row['kind'] == 'session' and row['id'] == session.id and Decimal(row['bar']) == 10000 for row in self.client.get('/').context['pending_bills']))
        self.assertEqual(self.client.post(f'/bar/payment/{sale.id}/').status_code, 200)
        self.assertEqual(self.client.post(f'/bar/payment/{sale.id}/').status_code, 409)
        self.assertEqual(self.client.get('/reports/').context['bar_total'], 10000)
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 8)

    def test_order_cannot_be_attached_to_finished_session(self):
        device = Table.objects.get(number=1)
        session = Session.objects.create(table=device, status='stopped')
        result = self.sell([{'id': self.water.id, 'quantity': 1}], table_id=device.id, session_id=session.id, defer_payment=True)
        self.assertEqual(result.status_code, 409)
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 10)
        self.assertFalse(BarSale.objects.exists())

    def test_insufficient_stock_rolls_back_every_item(self):
        response = self.sell([{'id': self.water.id, 'quantity': 3}, {'id': self.snack.id, 'quantity': 3}])
        self.assertEqual(response.status_code, 400)
        self.water.refresh_from_db()
        self.snack.refresh_from_db()
        self.assertEqual((self.water.stock, self.snack.stock), (10, 2))
        self.assertFalse(BarSale.objects.exists())
        self.assertFalse(BarSaleItem.objects.exists())

    def test_retry_with_same_request_key_does_not_charge_or_reduce_stock_twice(self):
        key = str(uuid.uuid4())
        items = [{'id': self.water.id, 'quantity': 2}]
        first = self.sell(items, request_key=key)
        second = self.sell(items, request_key=key)
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(first.json()['sale_id'], second.json()['sale_id'])
        self.assertEqual(first.json()['total'], second.json()['total'])
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 8)
        self.assertEqual(BarSale.objects.count(), 1)
        self.assertEqual(BarSaleItem.objects.count(), 1)

    def test_invalid_quantity_or_duplicate_items_leave_stock_unchanged(self):
        invalid_items = [
            [{'id': self.water.id, 'quantity': quantity}]
            for quantity in (0, -1, 1.5, True, 1001)
        ]
        invalid_items.append([{'id': self.water.id, 'quantity': 1}, {'id': self.water.id, 'quantity': 1}])
        for items in invalid_items:
            with self.subTest(items=items):
                self.assertEqual(self.sell(items).status_code, 400)
        self.water.refresh_from_db()
        self.assertEqual(self.water.stock, 10)
        self.assertFalse(BarSale.objects.exists())

    def test_non_staff_cannot_sell(self):
        self.client.logout()
        self.assertEqual(self.sell([{'id': self.water.id, 'quantity': 1}]).status_code, 302)
        self.assertFalse(BarSale.objects.exists())


class SettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('settings-admin', 'settings@example.com', 'password')
        self.client.force_login(self.user)

    def test_valid_rates_update_billiard_and_playstation(self):
        tables = list(Table.objects.order_by('number'))
        data = {f'rate_{table.id}': str(25000 + table.number * 1000) for table in tables}
        response = self.client.post('/settings/', data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['success'])
        for table in tables:
            table.refresh_from_db()
            self.assertEqual(table.price_per_hour, Decimal(data[f'rate_{table.id}']))
        self.assertEqual(Table.objects.filter(table_type='PlayStation').count(), 2)

    def test_active_table_rate_change_rolls_back_all_rates(self):
        tables = list(Table.objects.order_by('number'))
        original_rates = {table.id: table.price_per_hour for table in tables}
        active_table = tables[-1]
        Session.objects.create(table=active_table, start_time=timezone.now(), status='active')
        data = {f'rate_{table.id}': str(table.price_per_hour + 1000) for table in tables}
        response = self.client.post('/settings/', data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.context['success'])
        self.assertIn('o‘yin davom etmoqda', response.context['error'])
        self.assertEqual(dict(Table.objects.values_list('id', 'price_per_hour')), original_rates)

    def test_active_table_unchanged_rate_does_not_block_other_rates(self):
        tables = list(Table.objects.order_by('number'))
        active_table = tables[-1]
        Session.objects.create(table=active_table, start_time=timezone.now(), status='active')
        data = {f'rate_{table.id}': str(table.price_per_hour) for table in tables}
        data[f'rate_{tables[0].id}'] = '71000'
        self.assertEqual(self.client.post('/settings/', data).status_code, 200)
        tables[0].refresh_from_db()
        self.assertEqual(tables[0].price_per_hour, Decimal('71000'))

    def test_non_staff_cannot_change_rates(self):
        self.client.logout()
        self.assertEqual(self.client.post('/settings/', {}).status_code, 302)


class CombinedBillTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser('bill-admin', 'bill@example.com', 'password'))
        self.table = Table.objects.get(number=1)
        self.session = Session.objects.create(table=self.table, status='stopped', start_time=timezone.now(), end_time=timezone.now(), total_price=10000)
        self.sale = BarSale.objects.create(table=self.table, session=self.session, total=24000, payment_done=False, request_key=uuid.uuid4())
        BarSaleItem.objects.create(sale=self.sale, name='Cola', unit_price=12000, quantity=2)
        self.url = f'/bill/session/{self.session.pk}/'

    def pay(self, bill):
        return self.client.post(self.url, json.dumps({'due': bill['due'], 'unpaid_sales': bill['unpaid_sales']}), content_type='application/json')

    def test_combined_details_and_atomic_payment(self):
        bill = self.client.get(self.url).json()
        self.assertEqual(Decimal(bill['due']), 34000)
        self.assertEqual(bill['items'][0]['quantity'], 2)
        self.assertEqual(self.pay(bill).status_code, 200)
        self.session.refresh_from_db(); self.sale.refresh_from_db()
        self.assertTrue(self.session.payment_done)
        self.assertTrue(self.sale.payment_done)
        self.assertEqual(self.session.paid_at, self.sale.sold_at)
        self.assertEqual(self.pay(bill).status_code, 409)

    def test_prepaid_not_charged_twice(self):
        self.session.billing_type = 'prepaid'
        self.session.prepaid_amount = 10000
        self.session.payment_done = True
        self.session.save()
        bill = self.client.get(self.url).json()
        self.assertEqual(Decimal(bill['due']), 24000)
        self.assertEqual(Decimal(bill['paid']), 10000)
        self.assertEqual(self.pay(bill).status_code, 200)

    def test_stale_bill_does_not_partially_pay(self):
        bill = self.client.get(self.url).json()
        BarSale.objects.create(table=self.table, session=self.session, total=5000, payment_done=False, request_key=uuid.uuid4())
        self.assertEqual(self.pay(bill).status_code, 409)
        self.session.refresh_from_db(); self.sale.refresh_from_db()
        self.assertFalse(self.session.payment_done)
        self.assertFalse(self.sale.payment_done)

    def test_active_bill_cannot_pay_and_grouped_sidebar(self):
        self.session.status = 'active'; self.session.save()
        bill = self.client.get(self.url).json()
        self.assertEqual(self.pay(bill).status_code, 409)
        response = self.client.get('/')
        rows = response.context['pending_bills']
        self.assertEqual(sum(row['id'] == self.session.pk and row['kind'] == 'session' for row in rows), 1)
        self.assertNotContains(response, 'id="tab-bar"')
        self.assertEqual(self.client.get(f'/bill/sale/{self.sale.pk}/').status_code, 404)

    def test_standalone_sale_details_and_auth(self):
        self.sale.session = None; self.sale.save()
        url = f'/bill/sale/{self.sale.pk}/'
        bill = self.client.get(url).json()
        self.assertEqual(Decimal(bill['due']), 24000)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)


class ReservationTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser('reserve-admin', 'reserve@example.com', 'password'))
        self.table = Table.objects.get(number=1)

    def reserve(self, **extra):
        from datetime import timedelta
        payload = {'customer': 'Ali +998901234567', 'note': 'Deraza yonida', 'starts_at': (timezone.now() + timedelta(hours=2)).isoformat()}
        payload.update(extra)
        return self.client.post(f'/reserve/{self.table.id}/', json.dumps(payload), content_type='application/json')

    def test_reservation_warning_and_acknowledged_start(self):
        result = self.reserve()
        self.assertEqual(result.status_code, 200)
        reservation = result.json()['reservations'][0]
        self.assertEqual(reservation['customer'], 'Ali +998901234567')
        response = self.client.post(f'/start/{self.table.id}/', '{}', content_type='application/json')
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Session.objects.filter(table=self.table, status='active').exists())
        response = self.client.post(f'/start/{self.table.id}/', json.dumps({'reservation_ack': [reservation['id']]}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        row = next(t for t in self.client.get('/state/').json()['tables'] if t['id'] == self.table.id)
        self.assertEqual(len(row['reservations']), 1)

    def test_validation_cancel_and_auth(self):
        self.assertEqual(self.reserve(note='a' * 301).status_code, 400)
        self.assertEqual(self.reserve(starts_at='2020-01-01T12:00:00+05:00').status_code, 400)
        self.assertEqual(self.reserve(starts_at='bad').status_code, 400)
        reservation = self.reserve().json()['reservations'][0]
        result = self.client.post(f'/reserve/{self.table.id}/', json.dumps({'cancel': reservation['id']}), content_type='application/json')
        self.assertEqual(result.json()['reservations'], [])
        self.client.logout()
        self.assertEqual(self.reserve().status_code, 302)

    def test_note_only_reservation(self):
        response = self.reserve(customer='', note='Do‘stlar uchun')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['reservations'][0]['note'], 'Do‘stlar uchun')
