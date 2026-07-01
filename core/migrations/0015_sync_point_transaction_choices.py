from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_add_student_rating"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pointtransaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("signup_bonus", "Signup Bonus"),
                    ("lesson_taken", "Lesson Taken"),
                    ("lesson_taught", "Lesson Taught"),
                    ("purchase", "Purchase"),
                    ("withdrawal", "Withdrawal"),
                    ("transfer", "Transfer"),
                ],
                max_length=20,
            ),
        ),
    ]
