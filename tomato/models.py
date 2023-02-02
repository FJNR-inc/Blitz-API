from django.utils import timezone
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from blitz_api.services import send_mail


class Message(models.Model):
    """Messages of the tomato app chat"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
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
        settings.AUTH_USER_MODEL,
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

    def send_report_notification(self):
        """
        This function sends an automatic email to notify a user that his
        message has been reported in some specific categories
        """

        if 'Suicide ou automutilation' in self.reason:
            context = {
                'MESSAGE': self.message.message,
                'POSTED_AT': self.message.posted_at,
                'AUTHOR_FIRST_NAME': self.message.user.first_name,
                'AUTHOR_LAST_NAME': self.message.user.last_name,
                'AUTHOR_EMAIL': self.message.user.email,
            }

            response_send_mail = send_mail(
                [self.message.user.email],
                context,
                'REPORT_SUICIDE'
            )
            return response_send_mail

        return []


class Attendance(models.Model):
    """Attendances to the tomato app"""

    key = models.CharField(
        verbose_name=_("Random key"),
        max_length=300,
        unique=True,
    )

    longitude = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        verbose_name=_("Longitude"),
        null=True,
        blank=True,
    )

    latitude = models.DecimalField(
        max_digits=6,
        decimal_places=3,
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


class Tomato(models.Model):
    TOMATO_SOURCE_RETREAT = 'RETREAT'
    TOMATO_SOURCE_TIMESLOT = 'TIMESLOT'
    TOMATO_SOURCE_CHRONO = 'CHRONO'
    TOMATO_SOURCE_MANUAL = 'USER'

    TOMATO_SOURCE_CHOICES = (
        (TOMATO_SOURCE_RETREAT, _('Retreat')),
        (TOMATO_SOURCE_TIMESLOT, _('Timeslot')),
        (TOMATO_SOURCE_CHRONO, _('Chrono')),
        (TOMATO_SOURCE_MANUAL, _('User')),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='tomatoes',
    )

    number_of_tomato = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Number of tomato"),
    )

    source = models.CharField(
        max_length=255,
        choices=TOMATO_SOURCE_CHOICES,
    )

    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    content_object = GenericForeignKey(
        'content_type',
        'object_id'
    )

    acquisition_date = models.DateTimeField(
        verbose_name=_("Acquisition date"),
        default=timezone.now,
    )

    updated_at = models.DateTimeField(
        verbose_name=_("Updated at"),
        auto_now=True,
    )

    created_at = models.DateTimeField(
        verbose_name=_("Created at"),
        auto_now_add=True,
    )
