from rest_framework.generics import ListAPIView
from src.api.views.base import *


class TableListView(ListAPIView):
    queryset = TableModel.objects.all().order_by("number")
    serializer_class = TableSerializer
