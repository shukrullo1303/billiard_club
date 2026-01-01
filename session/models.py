from django.db import models
from django.utils import timezone
from table.models import Table

class Session(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('waiting_payment', 'Waiting Payment'),
        ('finished', 'Finished'),
    )

    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True, related_name='sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_done = models.BooleanField(default=False)
    


    def calculate_price(self):
        if not self.end_time:
            return 0
        seconds = (self.end_time - self.start_time).total_seconds()
        hours = seconds / 3600
        return round(hours * float(self.table.price_per_hour), 2)
