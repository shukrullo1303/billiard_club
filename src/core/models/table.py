from src.core.models.base import *


class TableModel(BaseModel):

    class TableType(models.TextChoices):
        BILLIARD = 'billiard', 'Billiard'
        TENNIS = 'tennis', 'Tennis'
        PS3 = 'ps3', 'PlayStation 3'

    number = models.PositiveIntegerField(unique=True)

    table_type = models.CharField(
        max_length=20,
        choices=TableType.choices,
        default=TableType.BILLIARD
    )

    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)

    is_active = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.number} - {self.table_type}"

    def start_session(self):
        self.is_active = True
        self.save(update_fields=['is_active'])

    def stop_session(self):
        self.is_active = False
        self.save(update_fields=['is_active'])
