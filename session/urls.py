from django.urls import path
from .views import DashboardView, StartSessionView, StopSessionView, PaySessionView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('start/<int:table_id>/', StartSessionView.as_view(), name='start_session'),
    path('stop/<int:table_id>/', StopSessionView.as_view(), name='stop_session'),
    path('payment/<int:session_id>/', PaySessionView.as_view(), name='pay_session'),
]
