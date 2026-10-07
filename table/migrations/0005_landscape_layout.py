from django.db import migrations


def landscape(apps, schema_editor):
    Table = apps.get_model('table', 'Table')
    # The supplied landscape plan: upper row 6–4–2, lower row 5–3–1.
    for number, x, y in [(6, 19, 25), (4, 50, 25), (2, 81, 25),
                         (5, 19, 76), (3, 50, 76), (1, 81, 76)]:
        Table.objects.filter(number=number).update(position_x=x, position_y=y, rotation=270)


class Migration(migrations.Migration):
    dependencies = [('table', '0004_initial_layout')]
    operations = [migrations.RunPython(landscape, migrations.RunPython.noop)]
