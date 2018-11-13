import re

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from .exceptions import MailServiceError
from django.core.mail import send_mail as django_send_mail


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
    language_field = re.compile('[a-z0-9_]+_[a-z]{2}$')
    data = {
        k: v for k, v in data_dict.items() if not language_field.match(k)
    }
    return data


def get_model_from_name(model_name):
    """
    Used to get a model instance when you only have its name.
    """
    app_labels = [a.label for a in apps.app_configs.values()]
    app_number = len(app_labels)
    for idx, app in enumerate(app_labels):
        try:
            model = apps.get_model(app, model_name)
            return model
        except LookupError as err:
            if idx == (app_number - 1):
                raise err
            continue


def notify_user_of_new_account(email, password):
    if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is False:
        raise MailServiceError(_("Email service is disabled."))
    else:
        merge_data = {
            'EMAIL': email,
            'PASSWORD': password,
        }

        plain_msg = render_to_string(
            "notify_user_of_new_account.txt",
            merge_data
        )
        msg_html = render_to_string(
            "notify_user_of_new_account.html",
            merge_data
        )

        return django_send_mail(
            "Bienvenue à Thèsez-vous?",
            plain_msg,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=msg_html,
        )
