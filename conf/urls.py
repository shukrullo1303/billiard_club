from django.contrib import admin
from django.urls import path, include
from table.views import TableDashboardView
from session.views import StartSessionView, StopSessionView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TableDashboardView.as_view(), name='dashboard'),
    path('sessions/start/<int:table_id>/', StartSessionView.as_view(), name='start-session'),
    path('sessions/stop/<int:table_id>/', StopSessionView.as_view(), name='stop-session'),
    # path('sessions/payment/<int:session_id>/', payment_view, name='session-payment'),
]


