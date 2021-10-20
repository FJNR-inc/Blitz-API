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


class Attendance(models.Model):
    """Attendances to the tomato app"""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='attendances',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True,
    )
