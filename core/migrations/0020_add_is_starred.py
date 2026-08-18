from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_add_student_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='is_starred',
            field=models.BooleanField(default=False),
        ),
    ]
