from django.db import migrations, models


def split_balances(apps, schema_editor):
    """既存の balance/earned_balance を student/teacher に振り分ける"""
    PointBalance = apps.get_model('core', 'PointBalance')
    for pb in PointBalance.objects.all():
        pb.teacher_balance = pb.earned_balance
        pb.student_balance = max(0, pb.balance - pb.earned_balance)
        pb.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_withdrawalrequest_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='pointbalance',
            name='student_balance',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='pointbalance',
            name='teacher_balance',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(split_balances, migrations.RunPython.noop),
        migrations.RemoveField(model_name='pointbalance', name='balance'),
        migrations.RemoveField(model_name='pointbalance', name='earned_balance'),
    ]
