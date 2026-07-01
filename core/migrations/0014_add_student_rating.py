from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_ensure_student_balance_10"),
    ]

    operations = [
        migrations.AddField(
            model_name="quicklessonmatch",
            name="student_rating",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="quicklessonmatch",
            name="student_rated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
