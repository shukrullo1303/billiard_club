from src.api.views.base import *


class TodayReportView(BaseView):

    def get(self, request):
        today = now().date()

        sessions = SessionModel.objects.filter(
            start_time__date=today,
            status=SessionModel.STATUS_FINISHED
        )

        total_sessions = sessions.count()
        total_income = sessions.aggregate(Sum("total_price"))["total_price__sum"] or 0

        payments = PaymentModel.objects.filter(paid_at__date=today)

        payment_breakdown = payments.values("payment_type").annotate(total=Sum("amount"))

        most_used_tables = (
            sessions.values("table__number")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        return Response({
            "total_sessions": total_sessions,
            "total_income": total_income,
            "payment_breakdown": payment_breakdown,
            "most_used_tables": most_used_tables
        })
