from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('table', '0006_club_plan')]
    operations = [migrations.AddField(model_name='barproduct', name='image', field=models.ImageField(blank=True, upload_to='bar/'))]
