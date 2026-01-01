# payment/admin.py
from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('session', 'amount', 'paid_at')
    search_fields = ('session__table__number',)
