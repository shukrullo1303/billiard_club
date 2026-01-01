from src.api.views.base import *


class OfflineSyncView(BaseView):
    """
    Frontend offline paytda yig‘ilgan sessionlarni bulk tarzda serverga yuklaydi.
    """

    def post(self, request):
        sessions = request.data.get("sessions", [])

        created = 0
        skipped = 0

        for data in sessions:
            table_id = data.get("table")
            start_time = data.get("start_time")
            end_time = data.get("end_time")

            if not table_id or not start_time:
                skipped += 1
                continue

            table = TableModel.objects.filter(id=table_id).first()
            if not table:
                skipped += 1
                continue

            # Duplikat kelib qolmasligi uchun
            exists = SessionModel.objects.filter(
                table=table,
                start_time=start_time
            ).exists()

            if exists:
                skipped += 1
                continue

            session = SessionModel.objects.create(
                table=table,
                start_time=start_time,
                end_time=end_time,
                status=SessionModel.STATUS_FINISHED
            )

            if end_time:
                session.total_price = session.calculate_price()
                session.save(update_fields=['total_price'])

            created += 1

        return Response({
            "created": created,
            "skipped": skipped
        }, status=status.HTTP_201_CREATED)
