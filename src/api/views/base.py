from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.utils.timezone import now
from django.db.models import Sum, Count
from django.shortcuts import get_object_or_404

from src.core.models import *
from src.api.serializers import *


class BaseView(APIView):
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['created_at'] = instance.created_at.strftime("%Y-%m-%d %H:%M")
        representation['updated_at'] = instance.updated_at.strftime("%Y-%m-%d %H:%M")
        return representation
    