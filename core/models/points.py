from django.db import models
from django.contrib.auth.models import User


class PointBalance(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='point_balance'
    )
    student_balance = models.IntegerField(default=0)  # 生徒ポイント: 購入・ボーナス
    teacher_balance = models.IntegerField(default=0)  # 講師ポイント: 授業で稼いだ分（出金可）

    @property
    def balance(self):
        """合計ポイント（表示用・後方互換）"""
        return self.student_balance + self.teacher_balance

    def __str__(self):
        return f"{self.user.username}: {self.student_balance}pt(student) + {self.teacher_balance}pt(teacher)"


class PointTransaction(models.Model):
    TYPE_SIGNUP_BONUS  = 'signup_bonus'
    TYPE_LESSON_TAKEN  = 'lesson_taken'
    TYPE_LESSON_TAUGHT = 'lesson_taught'
    TYPE_PURCHASE      = 'purchase'
    TYPE_WITHDRAWAL    = 'withdrawal'
    TYPE_TRANSFER      = 'transfer'   # 講師ポイント → 生徒ポイント

    TRANSACTION_TYPES = [
        (TYPE_SIGNUP_BONUS,  'Signup Bonus'),
        (TYPE_LESSON_TAKEN,  'Lesson Taken'),
        (TYPE_LESSON_TAUGHT, 'Lesson Taught'),
        (TYPE_PURCHASE,      'Purchase'),
        (TYPE_WITHDRAWAL,    'Withdrawal'),
        (TYPE_TRANSFER,      'Transfer'),
    ]

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_transactions')
    amount           = models.IntegerField()
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at       = models.DateTimeField(auto_now_add=True)
    reference_id     = models.IntegerField(null=True, blank=True)
    note             = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} {self.amount:+d}pt ({self.transaction_type})"


class WithdrawalRequest(models.Model):
    CURRENCY_CHOICES = [
        ('EUR', 'EUR (€)'),
        ('USD', 'USD ($)'),
        ('CHF', 'CHF (Fr.)'),
    ]
    METHOD_CHOICES = [
        ('wise',     'Wise'),
        ('paypal',   'PayPal'),
        ('bank',     'Bank Transfer'),
    ]
    STATUS_PENDING  = 'pending'
    STATUS_PAID     = 'paid'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING,  'Pending'),
        (STATUS_PAID,     'Paid'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='withdrawal_requests')
    points          = models.PositiveIntegerField()          # 引き出すポイント数（総額）
    fee             = models.PositiveIntegerField(default=0) # 手数料
    currency        = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    payment_method  = models.CharField(max_length=20, choices=METHOD_CHOICES)
    payment_details = models.TextField(help_text="口座番号・PayPalメール・WiseメールなどをテキストでOK")
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    admin_note      = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    processed_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def net_points(self):
        return self.points - self.fee

    def __str__(self):
        return f"{self.user.username} {self.points}pt → {self.currency} ({self.status})"
