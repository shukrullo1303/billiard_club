from django.urls import path
from src.api.views import *

urlpatterns = [
    path('tables/', TableListView.as_view()),
    path('sessions/<int:pk>/start/', StartSessionView.as_view()),
    path('sessions/<int:pk>/stop/', StopSessionView.as_view()),   
    path('sessions/pay/', PaymentView.as_view()),
    path('reports/today/', TodayReportView.as_view()),
    path('sync/sessions/', OfflineSyncView.as_view()),
]

