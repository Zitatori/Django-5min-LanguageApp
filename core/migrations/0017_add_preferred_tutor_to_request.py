from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_add_conversation_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='quicklessonrequest',
            name='preferred_tutor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='preferred_requests',
                to='core.tutorprofile',
            ),
        ),
    ]
