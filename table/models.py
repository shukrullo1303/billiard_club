from django.db import models

class Table(models.Model):
    number = models.PositiveIntegerField(unique=True)
    table_type = models.CharField(max_length=50, default="Standard")
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=0)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"Table {self.number}"
