from src.api.views.base import *


class PaymentView(BaseView):
    def post(self, request):
        session = get_object_or_404(SessionModel, id=request.data.get("session_id"))

        if session.status != SessionModel.STATUS_WAITING_PAYMENT:
            return Response({"error": "Session not ready for payment"}, status=400)

        PaymentModel.objects.create(
            session=session,
            amount=session.total_price,
            payment_type=request.data.get("payment_type", PaymentModel.PAYMENT_CASH)
        )

        session.status = SessionModel.STATUS_FINISHED
        session.save(update_fields=["status"])

        return Response({"status": "paid"})
