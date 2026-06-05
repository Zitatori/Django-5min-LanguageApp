from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class GoldMembership(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='gold_membership'
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_active(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        status = "active" if self.is_active else "expired"
        return f"Gold({status}) {self.user.username} until {self.expires_at:%Y-%m-%d}"


class GoldSubscriptionRequest(models.Model):
    STATUS_PENDING   = 'pending'
    STATUS_ACTIVATED = 'activated'
    STATUS_REJECTED  = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_ACTIVATED, 'Activated'),
        (STATUS_REJECTED,  'Rejected'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gold_requests')
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"GoldReq {self.user.username} ({self.status})"
