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
from blitz_api.testing_tools import CustomAPITestCase

from retirement.models import (
    RetreatType,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatTypeTests(CustomAPITestCase):

    @classmethod
    def setUpClass(cls):
        super(RetreatTypeTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreatType = RetreatType.objects.create(
            name="example 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,)

        self.retreatType2 = RetreatType.objects.create(
            name="different type",
            minutes_before_display_link=10,
            number_of_tomatoes=4,)

    def test_search_name_retreattype(self):
        """
        Ensure we can search a Retreat type by name
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('retreat:retreattype-list'),
            {
                'search': 'exam'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['results']), 1)
        self.assertEqual(content['results'][0]['name'], self.retreatType.name)
