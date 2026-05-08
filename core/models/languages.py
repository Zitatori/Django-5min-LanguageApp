from django.db import models


class LessonLanguage(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)

    def __str__(self) -> str:
        return self.name