from django.db import migrations


def arrange(apps, schema_editor):
    Table = apps.get_model('table', 'Table')
    for number, x, y in [(6, 19, 24), (5, 50, 24), (4, 81, 24),
                         (1, 19, 75), (2, 50, 75), (3, 81, 75)]:
        Table.objects.filter(number=number).update(position_x=x, position_y=y, rotation=270)


class Migration(migrations.Migration):
    dependencies = [('table', '0005_landscape_layout')]
    operations = [migrations.RunPython(arrange, migrations.RunPython.noop)]
