from django.contrib import admin
from django.urls import path, include
from session.views import StartSessionView, StopSessionView



urlpatterns = [
    path('admin/', admin.site.urls),
    # path('', TableDashboardView.as_view(), name='dashboard'),
    # path('sessions/start/<int:table_id>/', StartSessionView.as_view(), name='start-session'),
    # path('sessions/stop/<int:table_id>/', StopSessionView.as_view(), name='stop-session'),
    # path('sessions/payment/<int:session_id>/', payment_view, name='session-payment'),
    path('', include('session.urls')),
    path('reports/', include('reports.urls')),
    # path("dashboard-data/", DashboardDataView.as_view(), name="dashboard_data"),

]


