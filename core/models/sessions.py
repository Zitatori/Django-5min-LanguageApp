from django.db import models


class UpcomingSession(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('fr', 'French'),
        ('es', 'Spanish'),
        ('ja', 'Japanese'),
    ]
    TIMEZONE_CHOICES = [
        ('Europe/Zurich', 'Europe/Zurich (CET/CEST)'),
        ('Asia/Tokyo',    'Asia/Tokyo (JST)'),
    ]

    title      = models.CharField(max_length=200)
    start_time = models.DateTimeField(
        help_text="Stored as UTC internally. Django Admin shows it in the server timezone (Europe/Zurich)."
    )
    timezone   = models.CharField(max_length=50, choices=TIMEZONE_CHOICES, default='Asia/Tokyo')
    language   = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    tutor_count = models.PositiveSmallIntegerField(default=1)
    note       = models.CharField(max_length=500, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_time']
        verbose_name = 'Upcoming Session'
        verbose_name_plural = 'Upcoming Sessions'

    def __str__(self):
        return f"{self.start_time:%Y-%m-%d %H:%M} UTC — {self.get_language_display()}"
