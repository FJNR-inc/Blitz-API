import json

import pytz

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from blitz_api.factories import (
    AdminFactory,
    UserFactory,
)
from blitz_api import testing_tools
from blitz_api.testing_tools import CustomAPITestCase

from retirement.models import (
    RetreatType,
    AutomaticEmail,
)
User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class AutomaticEmailTests(CustomAPITestCase):
    ATTRIBUTES = testing_tools.AUTOMATIC_EMAIL_ATTRIBUTES

    @classmethod
    def setUpClass(cls):
        super(AutomaticEmailTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreatType_1 = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreatType_2 = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.auto_email_1 = AutomaticEmail.objects.create(
            minutes_delta=1,
            time_base=AutomaticEmail.TIME_BASE_AFTER_END,
            template_id='1',
            context='Auto email 1 context',
            retreat_type=self.retreatType_1
        )
        self.auto_email_2 = AutomaticEmail.objects.create(
            minutes_delta=1,
            time_base=AutomaticEmail.TIME_BASE_AFTER_END,
            template_id='1',
            context='Auto email 1 context',
            retreat_type=self.retreatType_1
        )
        self.auto_email_3 = AutomaticEmail.objects.create(
            minutes_delta=1,
            time_base=AutomaticEmail.TIME_BASE_AFTER_END,
            template_id='1',
            context='Auto email 1 context',
            retreat_type=self.retreatType_2
        )

    def test_create_as_user(self):
        """
        Ensure we can't create an automatic email as user
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'minutes_delta': 1,
            'time_base': AutomaticEmail.TIME_BASE_AFTER_END,
            'template_id': '1',
            'context': 'My user context',
            'retreat_type': reverse(
                'retreat:automaticemail-detail', args=[self.retreatType_1.id]),
        }

        response = self.client.post(
            reverse('retreat:automaticemail-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            response.content
        )

    def test_create_by_admin(self):
        """
        Ensure admin can create an automatic email.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'minutes_delta': 1,
            'time_base': AutomaticEmail.TIME_BASE_AFTER_END,
            'template_id': '1',
            'context': 'My user context',
            'retreat_type': reverse(
                'retreat:retreattype-detail', args=[self.retreatType_1.id]),
        }

        response = self.client.post(
            reverse('retreat:automaticemail-list'),
            data,
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )
        content = json.loads(response.content)
        self.check_attributes(content)

    def test_update_by_admin(self):
        """
        Ensure admin can update an automatic email.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'minutes_delta': 2,
            'time_base': AutomaticEmail.TIME_BASE_BEFORE_START,
            'template_id': '2',
            'context': 'Updated context',
            'retreat_type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType_2.id]),
        }

        response = self.client.patch(
            reverse(
                'retreat:automaticemail-detail',
                args=[self.auto_email_1.id]
            ),
            data,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content)
        updated_email = AutomaticEmail.objects.get(pk=self.auto_email_1.id)
        self.assertEqual(updated_email.minutes_delta, data['minutes_delta'])
        self.assertEqual(updated_email.time_base, data['time_base'])
        self.assertEqual(updated_email.template_id, data['template_id'])
        self.assertEqual(updated_email.context, data['context'])
        self.assertEqual(updated_email.retreat_type.id, self.retreatType_2.id)

    def test_update_by_user(self):
        """
        Ensure user can't update a retreat type.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'minutes_delta': 2,
            'time_base': AutomaticEmail.TIME_BASE_BEFORE_START,
            'template_id': '2',
            'context': 'Updated context',
            'retreat_type': reverse(
                'retreat:automaticemail-detail', args=[self.retreatType_2.id]),
        }

        response = self.client.patch(
            reverse(
                'retreat:automaticemail-detail',
                args=[self.auto_email_1.id]
            ),
            data,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_by_user(self):
        """
        Test that user can list auto email
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('retreat:automaticemail-list'),
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 3)
        self.check_attributes(content['results'][0])

    def test_list_by_retreat_type_by_admin(self):
        """
        Test that admin can list auto email by retreat type
        """
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse('retreat:automaticemail-list'),
            {
                'retreat_type': self.retreatType_1.id
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = json.loads(response.content)
        self.assertEqual(len(content['results']), 2)
        self.check_attributes(content['results'][0])
