from django.conf import settings
from django.db import models


class Clip(models.Model):
    """An X/Twitter status URL submitted for Valorant clip ranking."""

    url = models.URLField(
        max_length=500,
        unique=True,
        help_text='正規化した X 投稿 URL',
    )
    tweet_id = models.CharField(max_length=32, unique=True, db_index=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_clips',
    )
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Clip {self.tweet_id} ({self.view_count} views)'


class ViewEvent(models.Model):
    """One counted view, used for period rankings."""

    clip = models.ForeignKey(
        Clip,
        on_delete=models.CASCADE,
        related_name='view_events',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'View clip={self.clip_id} at {self.created_at}'


class Report(models.Model):
    class Reason(models.TextChoices):
        NOT_VALORANT = 'not_valorant', 'Valorant以外'
        COPYRIGHT = 'copyright', '権利侵害'
        OTHER = 'other', 'その他'

    clip = models.ForeignKey(
        Clip,
        on_delete=models.CASCADE,
        related_name='reports',
    )
    reason = models.CharField(max_length=32, choices=Reason.choices)
    detail = models.CharField(max_length=300, blank=True)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clip_reports',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report {self.get_reason_display()} on clip {self.clip_id}'
