from src.api.serializers.base import *


class PaymentSerializer(BaseSerializer):
    class Meta:
        model = PaymentModel
        fields = '__all__'