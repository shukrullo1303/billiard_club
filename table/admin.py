from django.contrib import admin
from .models import Table


admin.site.register(Table)
from .models import BarProduct
admin.site.register(BarProduct)

from .models import BarSale, BarSaleItem
admin.site.register(BarSale)
admin.site.register(BarSaleItem)
