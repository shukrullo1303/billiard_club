from rest_framework import serializers
from src.api.serializers.base import *
from src.api.serializers.sessions import SessionSerializer


class TableSerializer(BaseSerializer):
    current_session = serializers.SerializerMethodField()

    class Meta:
        model = TableModel
        fields = ['number', 'table_type', 'price_per_hour', 'is_active', 'current_session']

    def get_current_session(self, obj):
        session = obj.sessions.filter(status__in=['active','waiting_payment']).last()
        return SessionSerializer(session).data if session else None
