from rest_framework import serializers
from src.api.serializers.base import *

class SessionSerializer(serializers.ModelSerializer):
    table_name = serializers.CharField(source='table.name', read_only=True)

    class Meta:
        model = SessionModel
        fields = '__all__'
