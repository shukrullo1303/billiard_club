from django.db import models
from session.models import Session

class Payment(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_at = models.DateTimeField(auto_now_add=True)

    