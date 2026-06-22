import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_add_upcoming_session"),
    ]

    operations = [
        migrations.RemoveField(model_name="upcomingsession", name="title"),
        migrations.RemoveField(model_name="upcomingsession", name="timezone"),
        migrations.RemoveField(model_name="upcomingsession", name="language"),
        migrations.RemoveField(model_name="upcomingsession", name="tutor_count"),
        migrations.AlterField(
            model_name="upcomingsession",
            name="start_time",
            field=models.DateTimeField(),
        ),
        migrations.AddField(
            model_name="upcomingsession",
            name="end_time",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="upcomingsession",
            name="english_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="English tutors"),
        ),
        migrations.AddField(
            model_name="upcomingsession",
            name="french_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="French tutors"),
        ),
        migrations.AddField(
            model_name="upcomingsession",
            name="spanish_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Spanish tutors"),
        ),
        migrations.AddField(
            model_name="upcomingsession",
            name="japanese_count",
            field=models.PositiveSmallIntegerField(default=0, verbose_name="Japanese tutors"),
        ),
    ]
