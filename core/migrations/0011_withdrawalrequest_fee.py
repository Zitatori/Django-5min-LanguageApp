from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_update_upcoming_session'),
    ]

    operations = [
        migrations.AddField(
            model_name='withdrawalrequest',
            name='fee',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
