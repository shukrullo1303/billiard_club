from src.core.models.base import *


class SessionModel(BaseModel):

    STATUS_ACTIVE = 'active'
    STATUS_WAITING_PAYMENT = 'waiting_payment'
    STATUS_FINISHED = 'finished'

    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'),
        (STATUS_WAITING_PAYMENT, 'Waiting Payment'),
        (STATUS_FINISHED, 'Finished'),
    )

    table = models.ForeignKey(
        "TableModel",
        on_delete=models.SET_NULL,
        null=True,
        related_name='sessions'
    )

    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calculate_price(self):
        if not self.end_time or not self.table:
            return 0
        seconds = (self.end_time - self.start_time).total_seconds()
        hours = seconds / 3600
        return round(hours * float(self.table.price_per_hour), 2)

    def finish(self):
        self.end_time = timezone.now()
        self.total_price = self.calculate_price()
        self.status = self.STATUS_WAITING_PAYMENT
        self.save(update_fields=['end_time', 'total_price', 'status'])

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['table'],
                condition=models.Q(status='active'),
                name='unique_active_session_per_table'
            )
        ]
