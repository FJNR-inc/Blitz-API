import json
from datetime import datetime

import pytz
import re

from django.apps import apps
from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from django.template.loader import render_to_string

from rest_framework.pagination import PageNumberPagination

from log_management.models import Log
from .exceptions import MailServiceError
from django.core.mail import send_mail as django_send_mail

from rest_framework.utils.urls import remove_query_param, replace_query_param


LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


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
        try:
            # return number of successfully sent emails
            response = message.send()
        except Exception as err:
            additional_data = {
                'email': user.email,
                'context': context,
                'template': template
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise

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


def check_if_translated_field(field_name, data_dict):
    """
    Used to check if a field or one of its translated version is present in a
    dictionnary.
    ie:
        name or name_fr or name_en
    Returns:
        True: one or more occurences
        False: no occurence
    """
    if field_name in data_dict:
        return True
    for lang in settings.LANGUAGES:
        if data_dict.get(''.join([field_name, "_", lang[0]])):
            return True
    return False


def getMessageTranslate(field_name, data_dict, only_one_required=False):
    err = {}
    messageError = _("This field is required.")
    err[field_name] = messageError
    if only_one_required:
        messageError = _(
            "One of the two fields %(field)s must be completed."
        ) % {'field': field_name}

    for lang in settings.LANGUAGES:
        field_name_lang = ''.join([field_name, "_", lang[0]])
        for key in data_dict:
            if key == field_name_lang:
                err[field_name_lang] = messageError
                break
    return err


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

        try:
            return django_send_mail(
                "Bienvenue à Thèsez-vous?",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=msg_html,
            )
        except Exception as err:
            additional_data = {
                'title': "Bienvenue à Thèsez-vous?",
                'default_from': settings.DEFAULT_FROM_EMAIL,
                'user_email': email,
                'merge_data': merge_data,
                'template': 'notify_user_of_new_account'
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise


def notify_user_of_change_email(email, activation_url, first_name):
    if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is False:
        raise MailServiceError(_("Email service is disabled."))
    else:
        merge_data = {
            "ACTIVATION_URL": activation_url,
            "FIRST_NAME": first_name,
        }

        plain_msg = render_to_string(
            "notify_user_of_change_email.txt",
            merge_data
        )
        msg_html = render_to_string(
            "notify_user_of_change_email.html",
            merge_data
        )

        try:
            return django_send_mail(
                "Confirmation de votre nouvelle adresse courriel",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                html_message=msg_html,
            )
        except Exception as err:
            additional_data = {
                'title': "Confirmation de votre nouvelle adresse courriel",
                'default_from': settings.DEFAULT_FROM_EMAIL,
                'user_email': email,
                'merge_data': merge_data,
                'template': 'notify_user_of_change_email'
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise


class ExportPagination(PageNumberPagination):
    """ Custom paginator for data exportation """
    page_size = 1000
    page_size_query_param = 'page_size'
    max_page_size = 1000

    def get_paginated_response(self, data):
        next_url = self.get_next_link()
        previous_url = self.get_previous_link()
        first_url = self.get_first_link()
        last_url = self.get_last_link()

        links = []
        for url, label in (
                    (first_url, 'first'),
                    (previous_url, 'prev'),
                    (next_url, 'next'),
                    (last_url, 'last'),
                ):
            if url is not None:
                links.append('<{}>; rel="{}"'.format(url, label))

        response = HttpResponse(
            data,
            content_type="application/vnd.ms-excel"
        )
        # Add pagination links to response
        response['Link'] = ', '.join(links) if links else {}

        return response

    def get_first_link(self):
        if not self.page.has_previous():
            return None
        else:
            url = self.request.build_absolute_uri()
            return remove_query_param(url, self.page_query_param)

    def get_last_link(self):
        if not self.page.has_next():
            return None
        else:
            url = self.request.build_absolute_uri()
            return replace_query_param(
                url,
                self.page_query_param,
                self.page.paginator.num_pages,
            )
