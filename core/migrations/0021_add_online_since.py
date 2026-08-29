from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_add_is_starred"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutorprofile",
            name="online_since",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
