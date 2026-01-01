from django.urls import path
from . import views

app_name = 'reports'   # <-- shu qator kerak!

urlpatterns = [
    path('', views.MonthlySelectView.as_view(), name='monthly_select'),
    path('table/', views.MonthlyTableView.as_view(), name='monthly_table'),
]
