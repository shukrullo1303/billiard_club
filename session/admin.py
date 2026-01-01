# session/admin.py
from django.contrib import admin
from .models import Session

# @admin.register(Session)
# class SessionAdmin(admin.ModelAdmin):
#     list_display = ('table', 'start_time', 'end_time', 'payment_done', 'total_price')
#     list_filter = ('table', 'payment_done')
#     search_fields = ('table__number',)

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('table', 'start_time', 'end_time', 'payment_done', 'total_price', 'total_today')
    list_filter = ['start_time']

    def total_today(self, obj):
        from django.utils import timezone
        today = timezone.now().date()
        if obj.end_time and obj.end_time.date() == today and obj.payment_done:
            return obj.total_price
        return 0
    total_today.short_description = "Bugungi foyda"


