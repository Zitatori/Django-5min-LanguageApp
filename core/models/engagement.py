from django.conf import settings
from django.db import models


class LearningEvent(models.Model):
    """First purchase-page visit after two completed lessons, no tracking payload."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'kind'], name='unique_learning_event')]
