from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_add_referral_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='quicklessonmatch',
            name='student_feedback',
            field=models.TextField(blank=True, default='', max_length=500),
        ),
    ]
