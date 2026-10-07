from decimal import Decimal, ROUND_CEILING

from django.db import models, transaction
from django.utils import timezone
from table.models import Table


class Session(models.Model):
    STATUS_CHOICES = (("active", "Active"), ("stopped", "Stopped"))
    BILLING_CHOICES = (("metered", "Vaqt bo‘yicha"), ("prepaid", "Oldindan to‘lov"))

    # Receipts remain available even after a device is removed from the club.
    table = models.ForeignKey(Table, related_name="sessions", on_delete=models.SET_NULL, null=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    payment_done = models.BooleanField(default=False)
    billing_type = models.CharField(max_length=10, choices=BILLING_CHOICES, default="metered")
    prepaid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    device_type = models.CharField(max_length=50, default='Standard')
    device_name = models.CharField(max_length=100, blank=True, default='')

    def save(self, *args, **kwargs):
        if self._state.adding and self.table_id:
            self.device_type = self.table.table_type
            self.device_name = self.device_name or self.table.display_name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.device_name or (self.table.display_name if self.table else 'O‘chirilgan stol')} - {self.status}"

    def calculate_total(self, live=False, at=None):
        if self.billing_type == 'prepaid':
            amount = self.prepaid_amount
        elif self.start_time and self.table_id:
            end = self.end_time or (at or timezone.now())
            seconds = max(Decimal('0'), Decimal(str((end - self.start_time).total_seconds())))
            raw_amount = seconds * self.table.price_per_hour / Decimal('3600')
            amount = (raw_amount / Decimal('1000')).to_integral_value(rounding=ROUND_CEILING) * Decimal('1000')
        else:
            amount = self.total_price
        if not live:
            self.total_price = amount
            self.save(update_fields=['total_price'])
        return amount


@transaction.atomic
def settle_expired_sessions(now=None):
    """Settle prepaid games at their deadline, including time spent offline."""
    now = now or timezone.now()
    pending = Session.objects.filter(status='active', billing_type='prepaid', scheduled_end__lte=now)
    table_ids = list(pending.exclude(table_id=None).values_list('table_id', flat=True).distinct())
    # Other session actions lock the table first; keep that lock order here.
    list(Table.objects.select_for_update().filter(pk__in=table_ids).order_by('pk'))
    expired = list(pending.select_for_update().order_by('pk'))
    for session in expired:
        session.end_time = session.scheduled_end
        session.status = 'stopped'
        session.total_price = session.prepaid_amount
        session.payment_done = True
        session.paid_at = session.paid_at or session.start_time or session.scheduled_end
        session.save(update_fields=['end_time', 'status', 'total_price', 'payment_done', 'paid_at'])
    for table_id in table_ids:
        if not Session.objects.filter(table_id=table_id, status='active').exists():
            Table.objects.filter(pk=table_id).update(is_active=False)
    return expired
