from django.db import models
from src.core.models.base import BaseModel


class PaymentModel(BaseModel):

    PAYMENT_CASH = 'cash'
    PAYMENT_CARD = 'card'
    PAYMENT_CLICK = 'click'
    PAYMENT_PAYME = 'payme'

    PAYMENT_TYPE_CHOICES = (
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_CARD, 'Card'),
        (PAYMENT_CLICK, 'Click'),
        (PAYMENT_PAYME, 'Payme'),
    )

    session = models.OneToOneField("SessionModel", on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default=PAYMENT_CASH)
    paid_at = models.DateTimeField(auto_now_add=True)
    # is_partial = models.BooleanField(default=False)
