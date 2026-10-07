import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('table', '0009_barsale'), ('session', '0005_prepaid_sessions')]
    operations = [
        migrations.AddField(model_name='barsale', name='payment_done', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='barsale', name='session', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bar_orders', to='session.session')),
    ]
