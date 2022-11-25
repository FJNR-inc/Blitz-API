import traceback
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Log(models.Model):

    LEVEL_ERROR = 'ERROR'
    LEVEL_INFO = 'INFO'
    LEVEL_DEBUG = 'DEBUG'

    source = models.CharField(
        max_length=100,
        verbose_name=_("Source"),
    )

    level = models.CharField(
        max_length=100,
        verbose_name=_("Level"),
    )

    message = models.TextField(
        verbose_name=_("Message"),
    )

    error_code = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_("Error Code"),
    )

    additional_data = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Additional data"),
    )

    traceback_data = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("TraceBack"),
    )
    created = models.DateTimeField(
        verbose_name="Creation date",
        auto_now_add=True,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Log")
        verbose_name_plural = _("Logs")

    @classmethod
    def error(cls, source, message, error_code=None, additional_data=None):
        traceback_data = ''.join(traceback.format_stack(limit=10))
        new_log = Log(
            level=cls.LEVEL_ERROR,
            source=source,
            message=message,
            traceback_data=traceback_data
        )

        if error_code:
            new_log.error_code = error_code
        if additional_data:
            new_log.additional_data = additional_data

        new_log.save()

        return new_log


class EmailLog(models.Model):

    user_email = models.CharField(
        max_length=1024,
        verbose_name=_("User email")
    )

    type_email = models.CharField(
        max_length=1024,
        verbose_name=_("Type email")
    )

    nb_email_sent = models.IntegerField(
        verbose_name=_("Number email sent")
    )

    created = models.DateTimeField(
        verbose_name="Creation date",
        auto_now_add=True
    )

    class Meta:
        verbose_name = _("Email Log")
        verbose_name_plural = _("Email Logs")

    @classmethod
    def add(cls, user_email, type_email, nb_email_sent):

        new_email_log = cls.objects.create(
            user_email=user_email,
            type_email=type_email,
            nb_email_sent=nb_email_sent
        )

        return new_email_log


class ActionLog(models.Model):

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='action_logs',
        null=True,
        blank=True
    )

    session_key = models.CharField(
        verbose_name=_("Session key"),
        max_length=300,
    )

    source = models.CharField(
        max_length=100,
        verbose_name=_("Source"),
    )

    action = models.CharField(
        max_length=100,
        verbose_name=_("Action"),
    )

    additional_data = models.JSONField(
        verbose_name=_("Additional data"),
        blank=True,
        null=True,
    )

    created = models.DateTimeField(
        verbose_name="Creation date",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Action Log")
        verbose_name_plural = _("Action Logs")

    @classmethod
    def anonymize_data(cls, start_date=None, end_date=None):
        """
        Return a list of dict, one per ActionLog, where any reference to a
        user has been modified to a new UUID. We only want either the user
        or the session in a user column
        :params start_date: date to filter the range
        :params end_date: date to filter the range
        return nothing but will send an email when export is ready
        """
        anonymized_data = []
        user_uuid_matching = {}
        session_uuid_matching = {}
        if start_date and end_date:
            queryset = cls.objects.filter(
                created__gte=start_date,
                created__lte=end_date,
            )
        else:
            queryset = cls.objects.all()

        for action in queryset:
            anonymized_action = {}
            if action.user:
                if action.user not in user_uuid_matching:
                    user_uuid_matching[action.user] = str(uuid.uuid4())
                anonymized_action["user"] = user_uuid_matching[action.user]
            else:
                if action.session_key not in session_uuid_matching:
                    session_uuid_matching[action.session_key] = str(
                        uuid.uuid4(),
                    )
                anonymized_action["user"] = session_uuid_matching[
                    action.session_key
                ]
            anonymized_action["source"] = action.source
            anonymized_action["action"] = action.action
            anonymized_action["additional_data"] = action.additional_data
            anonymized_action["created"] = action.created
            anonymized_data.append(anonymized_action)
        return anonymized_data
