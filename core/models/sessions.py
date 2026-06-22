from django.db import models


class UpcomingSession(models.Model):
    # 開始・終了はUTC保存（フォームではJST入力→変換）
    start_time = models.DateTimeField()
    end_time   = models.DateTimeField()

    # 言語ごとの講師人数（0 = その言語は今回なし）
    english_count  = models.PositiveSmallIntegerField(default=0, verbose_name='English tutors')
    french_count   = models.PositiveSmallIntegerField(default=0, verbose_name='French tutors')
    spanish_count  = models.PositiveSmallIntegerField(default=0, verbose_name='Spanish tutors')
    japanese_count = models.PositiveSmallIntegerField(default=0, verbose_name='Japanese tutors')

    note         = models.CharField(max_length=500, blank=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_time']
        verbose_name        = 'Upcoming Session'
        verbose_name_plural = 'Upcoming Sessions'

    def __str__(self):
        from zoneinfo import ZoneInfo
        jst = self.start_time.astimezone(ZoneInfo('Asia/Tokyo'))
        return f"{jst:%Y-%m-%d %H:%M} JST"

    @property
    def language_counts(self):
        """表示用: 0より大きい言語だけ返す"""
        result = []
        if self.english_count  > 0: result.append(('en', 'English',  self.english_count))
        if self.french_count   > 0: result.append(('fr', 'French',   self.french_count))
        if self.spanish_count  > 0: result.append(('es', 'Spanish',  self.spanish_count))
        if self.japanese_count > 0: result.append(('ja', 'Japanese', self.japanese_count))
        return result
