from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_structured_conversation_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='tutorprofile',
            name='is_hourly_paid',
            field=models.BooleanField(default=False),
        ),
    ]
