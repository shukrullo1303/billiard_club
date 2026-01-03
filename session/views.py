from django.views.generic import TemplateView, View
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum

from table.models import Table
from .models import Session

import math
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator


@method_decorator(staff_member_required, name='dispatch')
class StartSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        table.is_active = True
        table.save()

        session = Session.objects.create(
            table=table,
            start_time=timezone.now(),
            status="active"
        )
        return JsonResponse({"success": True, "start_time": session.start_time.isoformat(), "session_id": session.id})



@method_decorator(staff_member_required, name='dispatch')
class StopSessionView(View):
    def post(self, request, table_id):
        table = Table.objects.get(id=table_id)
        table.is_active = False
        table.save()

        # Aktiv sessionni olish
        session = table.sessions.filter(status="active").last()
        if session:
            session.end_time = timezone.now()
            session.status = "stopped"

            # Total hisoblash (calculate_total metodidan foydalanamiz)
            session.calculate_total()

            # Minglar xonasigacha yaxlitlash
            session.total_price = math.ceil(session.total_price / 1000) * 1000
            session.save()

        return JsonResponse({
            "success": True,
            "session": {
                "id": session.id,
                "table_number": table.number,
                "price": session.total_price
            }
        })



@method_decorator(staff_member_required, name='dispatch')
class PaySessionView(View):
    def post(self, request, session_id):
        session = Session.objects.get(id=session_id)

        session.payment_done = True
        session.status = "paid"
        session.save()

        # bugungi jami foyda
        today = timezone.now().date()
        total_income = Session.objects.filter(
            payment_done=True,
            end_time__date=today
        ).aggregate(s=Sum("total_price"))["s"] or 0

        return JsonResponse({
            "success": True,
            "total_income": total_income
        })



@method_decorator(staff_member_required, name='dispatch')
class LivePriceAPIView(View):
    def get(self, request, table_id):
        session = Session.objects.filter(table_id=table_id, status="active").first()
        if not session:
            return JsonResponse({"active": False})

        total = session.calculate_total(live=True)
        return JsonResponse({
            "active": True,
            "price": total
        })
