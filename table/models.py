from django.db import models
from django.utils import timezone

class Table(models.Model):
    number = models.PositiveIntegerField(unique=True)
    table_type = models.CharField(max_length=50, default="Standard")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=0)
    is_active = models.BooleanField(default=False)
    position_x = models.FloatField(default=50)
    position_y = models.FloatField(default=50)
    rotation = models.PositiveSmallIntegerField(default=0)

    @property
    def display_name(self):
        return f"PS {self.number - 6}" if self.table_type == 'PlayStation' else f"{self.number}-stol"

    def __str__(self):
        return self.display_name


class BarProduct(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, default="Ichimliklar")
    price = models.DecimalField(max_digits=10, decimal_places=0)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='bar/', blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class BarSale(models.Model):
    sold_at = models.DateTimeField(default=timezone.now)
    table = models.ForeignKey(Table, null=True, blank=True, on_delete=models.SET_NULL, related_name='bar_sales')
    total = models.DecimalField(max_digits=12, decimal_places=0)
    request_key = models.UUIDField(unique=True)
    payment_done = models.BooleanField(default=True)
    session = models.ForeignKey('session.Session', null=True, blank=True, on_delete=models.SET_NULL, related_name='bar_orders')

    class Meta:
        ordering = ['-sold_at', '-id']


class BarSaleItem(models.Model):
    sale = models.ForeignKey(BarSale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(BarProduct, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100)
    unit_price = models.DecimalField(max_digits=10, decimal_places=0)
    quantity = models.PositiveIntegerField()


class Reservation(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    customer = models.CharField(max_length=100)
    note = models.CharField(max_length=300, blank=True)
    starts_at = models.DateTimeField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['starts_at', 'id']
