import re

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.translation import ugettext_lazy as _

from .exceptions import MailServiceError


def send_mail(users, context, template):
    """
    Uses Anymail to send templated emails.
    Returns a list of email addresses to which emails failed to be delivered.
    """
    if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is False:
        raise MailServiceError(_(
            "Email service is disabled."
        ))
    MAIL_SERVICE = settings.ANYMAIL

    failed_emails = list()
    for user in users:
        message = EmailMessage(
            subject=None,  # required for SendinBlue templates
            body='',  # required for SendinBlue templates
            to=[user.email]
        )
        message.from_email = None  # required for SendinBlue templates
        # use this SendinBlue template
        message.template_id = MAIL_SERVICE["TEMPLATES"].get(template)
        message.merge_global_data = context
        response = message.send()  # return number of successfully sent emails

        if not response:
            failed_emails.append(user.email)

    return failed_emails


def remove_translation_fields(data_dict):
    """
    Used to removed translation fields.
    It matches ANYTHING followed by "_" and a 2 letter code.
    ie:
        name_fr (matches)
        reservation_date (doesn't match)
    """
    language_field = re.compile('[a-z]+_[a-z]{2}$')
    data = {
        k: v for k, v in data_dict.items() if not language_field.match(k)
    }
    return data
