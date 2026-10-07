from django.db import migrations


def seed_playstations(apps, schema_editor):
    Table = apps.get_model('table', 'Table')
    for number in (7, 8):
        Table.objects.get_or_create(number=number, defaults={
            'table_type': 'PlayStation', 'price_per_hour': 30000,
            'position_x': 50, 'position_y': 50, 'rotation': 0,
        })


class Migration(migrations.Migration):
    dependencies = [('table', '0007_barproduct_image')]
    operations = [migrations.RunPython(seed_playstations, migrations.RunPython.noop)]
