from django.db import migrations

INITIAL_STUDENT_PTS = 10


def ensure_student_balance(apps, schema_editor):
    """全ユーザーの生徒ポイントを最低10ptに設定する。
    PointBalanceが存在しないユーザーには新規作成。
    既に10pt以上持っているユーザーはそのまま。
    """
    User = apps.get_model('auth', 'User')
    PointBalance = apps.get_model('core', 'PointBalance')

    existing_ids = set(PointBalance.objects.values_list('user_id', flat=True))

    # PointBalanceがないユーザーに新規作成
    new_balances = []
    for user in User.objects.exclude(id__in=existing_ids):
        new_balances.append(PointBalance(user=user, student_balance=INITIAL_STUDENT_PTS, teacher_balance=0))
    if new_balances:
        PointBalance.objects.bulk_create(new_balances)

    # 既存ユーザーのうち10pt未満を10ptに引き上げ
    PointBalance.objects.filter(student_balance__lt=INITIAL_STUDENT_PTS).update(
        student_balance=INITIAL_STUDENT_PTS
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_split_point_balances'),
    ]

    operations = [
        migrations.RunPython(ensure_student_balance, migrations.RunPython.noop),
    ]
