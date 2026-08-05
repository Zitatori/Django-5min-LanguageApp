from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_add_preferred_tutor_to_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='referral_source',
            field=models.CharField(blank=True, default='', max_length=300),
        ),
    ]
