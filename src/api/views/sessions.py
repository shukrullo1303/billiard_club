from src.api.views.base import *

class StartSessionView(BaseView):
    def post(self, request, pk): # URL ichidagi <int:pk> ni qabul qiladi
        table = get_object_or_404(TableModel, id=pk)

        # Stol bandligini tekshirish
        if SessionModel.objects.filter(table=table, status='active').exists():
            return Response({"error": "Stol band!"}, status=400)

        # Sessiya yaratish
        session = SessionModel.objects.create(table=table)
        table.start_session() # Stolni modelda band qilish

        return Response({"session_id": session.id, "status": "started"}, status=201)

class StopSessionView(BaseView):
    def post(self, request, pk): # pk argumenti keladi
        table = get_object_or_404(TableModel, id=pk)
        session = SessionModel.objects.filter(table=table, status='active').last()
        
        if not session:
            return Response({"error": "Sessiya topilmadi!"}, status=400)

        session.finish()
        table.stop_session()
        return Response({"message": "To'xtatildi", "price": session.total_price}, status=200)