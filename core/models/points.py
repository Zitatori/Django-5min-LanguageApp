from django.db import models
from django.contrib.auth.models import User


class PointBalance(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='point_balance'
    )
    balance = models.IntegerField(default=0)
    # earned_balance: lesson_taught で稼いだ分のみ（引き出し可能額）
    earned_balance = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.username}: {self.balance}pt"


class PointTransaction(models.Model):
    TYPE_SIGNUP_BONUS  = 'signup_bonus'
    TYPE_LESSON_TAKEN  = 'lesson_taken'
    TYPE_LESSON_TAUGHT = 'lesson_taught'
    TYPE_PURCHASE      = 'purchase'
    TYPE_WITHDRAWAL    = 'withdrawal'

    TRANSACTION_TYPES = [
        (TYPE_SIGNUP_BONUS,  'Signup Bonus'),
        (TYPE_LESSON_TAKEN,  'Lesson Taken'),
        (TYPE_LESSON_TAUGHT, 'Lesson Taught'),
        (TYPE_PURCHASE,      'Purchase'),
        (TYPE_WITHDRAWAL,    'Withdrawal'),
    ]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    amount           = models.IntegerField()          # 正 = 加算 / 負 = 減算
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at       = models.DateTimeField(auto_now_add=True)
    reference_id     = models.IntegerField(null=True, blank=True)  # match_id など
    note             = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.amount:+d}pt ({self.transaction_type})"
