import json

from datetime import timedelta
from unittest import mock

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.test.utils import override_settings

from .. import mailchimp
from ..factories import UserFactory, AdminFactory
from ..models import (ActionToken, Organization, Domain,
                      AcademicField, AcademicLevel)
from ..services import remove_translation_fields
from store.models import Membership

User = get_user_model()


class MailChimpTests(APITestCase):

    def setUp(self):
        self.email = 'jeffyer3813@gmail.com'
        self.first_name = 'john'
        self.last_name = 'doe'

    def test_get_member(self):
        self.assertFalse(mailchimp.is_email_on_list(self.email))

    def test_add_member(self):
        mailchimp.add_to_list(
            self.email,
            self.first_name,
            self.last_name)
