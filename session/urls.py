from django.urls import path
from .views import StartSessionView, StopSessionView, PaySessionView, StateView
from table.views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('start/<int:table_id>/', StartSessionView.as_view(), name='start_session'),
    path('stop/<int:table_id>/', StopSessionView.as_view(), name='stop_session'),
    path('payment/<int:session_id>/', PaySessionView.as_view(), name='pay_session'),
    path('state/', StateView.as_view(), name='session_state'),
]

from table.views import LayoutView, ProductView
urlpatterns += [
    path('layout/save/', LayoutView.as_view(), name='save_layout'),
    path('bar/save/', ProductView.as_view(), name='save_product'),
]

from table.views import ProductImageView, SettingsView, BarSaleView
urlpatterns += [
    path('bar/image/<int:product_id>/', ProductImageView.as_view(), name='product_image'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('bar/sale/', BarSaleView.as_view(), name='bar_sale'),
]

from table.views import PayBarSaleView
urlpatterns += [path('bar/payment/<int:sale_id>/', PayBarSaleView.as_view(), name='pay_bar_sale')]

from table.billing import BillView
urlpatterns += [path('bill/<str:kind>/<int:pk>/', BillView.as_view(), name='bill')]

from table.reservations import ReservationView
urlpatterns += [path('reserve/<int:table_id>/', ReservationView.as_view(), name='reserve')]
