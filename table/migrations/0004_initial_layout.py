from django.db import migrations


def arrange(apps, schema_editor):
    Table = apps.get_model('table', 'Table')
    for number in range(1, 7):
        table, _ = Table.objects.get_or_create(number=number, defaults={'price_per_hour': 50000})
        table.position_x = 73 if number <= 3 else 27
        table.position_y = 20 + ((number - 1) % 3) * 30
        table.rotation = 0 if number <= 3 else 90
        table.save(update_fields=['position_x', 'position_y', 'rotation'])


class Migration(migrations.Migration):
    dependencies = [('table', '0003_barproduct_table_position_x_table_position_y_and_more')]
    operations = [migrations.RunPython(arrange, migrations.RunPython.noop)]
