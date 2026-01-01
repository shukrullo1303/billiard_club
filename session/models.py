from django.db import models
from django.utils import timezone
from table.models import Table

class Session(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("stopped", "Stopped"),
    )
    
    table = models.ForeignKey(Table, related_name="sessions", on_delete=models.CASCADE)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="stopped")
    payment_done = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.table.number} - {self.status}"

    def calculate_total(self):
        if self.start_time and self.end_time:
            diff_hours = (self.end_time - self.start_time).total_seconds() / 3600
            self.total_price = diff_hours * float(self.table.price_per_hour)
            self.save()
