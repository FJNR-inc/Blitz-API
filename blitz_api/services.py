from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from imailing.Mailing import IMailing

from .exceptions import MailServiceError


def send_mail(users, context, template):
    """
    Uses Imailing to send templated emails.
    Returns a list of email addresses to which emails failed to be delivered.
    """
    if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is False:
        raise MailServiceError(_(
            "Email service is disabled."
        ))
    MAIL_SERVICE = settings.SETTINGS_IMAILING

    email = IMailing.create_instance(
        MAIL_SERVICE["SERVICE"],
        MAIL_SERVICE["API_KEY"],
    )
    failed_emails = list()
    for user in users:
        response = email.send_templated_email(
            email_from=MAIL_SERVICE["EMAIL_FROM"],
            template_id=MAIL_SERVICE["TEMPLATES"].get(template),
            list_to=[user.email],
            context=context,
        )

        if response["code"] == "failure":
            failed_emails.append(user.email)

    return failed_emails
