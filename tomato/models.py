from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _


User = get_user_model()


class Message(models.Model):
    """Messages of the tomato app chat"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='messages',
    )

    message = models.CharField(
        verbose_name=_('Message'),
        max_length=300,
    )

    posted_at = models.DateTimeField(
        verbose_name=_("Posted at"),
        auto_now_add=True,
    )


class Report(models.Model):
    """Report on the tomato app chat"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='reports',
    )

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        verbose_name=_("Message"),
        related_name='reports',
    )

    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True,
    )

    reason = models.CharField(
        verbose_name=_("Reason"),
        max_length=300,
    )


class Attendance(models.Model):
    """Attendances to the tomato app"""

    key = models.CharField(
        verbose_name=_("Random key"),
        max_length=300,
        unique=True,
    )

    longitude = models.DecimalField(
        max_digits=18,
        decimal_places=15,
        verbose_name=_("Longitude"),
        null=True,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=18,
        decimal_places=15,
        verbose_name=_("Latitude"),
        null=True,
        blank=True,
    )

    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"),
        auto_now=True,
    )

    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True,
    )
