import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('table', '0008_seed_ps')]
    operations = [
        migrations.CreateModel(name='BarSale', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('sold_at', models.DateTimeField(default=django.utils.timezone.now)),
            ('total', models.DecimalField(max_digits=12, decimal_places=0)),
            ('request_key', models.UUIDField(unique=True)),
            ('table', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bar_sales', to='table.table')),
        ], options={'ordering': ['-sold_at', '-id']}),
        migrations.CreateModel(name='BarSaleItem', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=100)),
            ('unit_price', models.DecimalField(max_digits=10, decimal_places=0)),
            ('quantity', models.PositiveIntegerField()),
            ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='table.barsale')),
            ('product', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='table.barproduct')),
        ]),
    ]
