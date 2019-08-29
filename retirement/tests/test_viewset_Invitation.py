import json
from datetime import datetime

import pytz

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient, APITestCase, APIRequestFactory

from blitz_api.factories import AdminFactory, UserFactory
from store.models import Coupon

from ..models import Retreat

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class InvitationViewTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(InvitationViewTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):

        self.retreat_type = ContentType.objects.get_for_model(Retreat)
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
        )

        self.coupon = Coupon.objects.create(
            value=13,
            code="ABCDEFGH",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=self.user,
        )
        self.coupon.applicable_retreats.add(self.retreat)
        self.coupon.applicable_product_types.add(self.retreat_type)

        factory = APIRequestFactory()
        self.request = factory.get('/')

    def test_create(self):

        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse('retreat:retreat-detail',
                               args=[self.retreat.id],
                               request=self.request),
            'nb_places': 4
        }

        response = self.client.post(
            reverse('retreat:retreatinvitation-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.assertEqual(
            response_data.get('nb_places'),
            data.get('nb_places')
        )

        self.assertEqual(
            response_data.get('retreat'),
            data.get('retreat')
        )

        self.assertEqual(
            response_data.get('coupon'),
            None
        )

        url = settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'FORGOT_PASSWORD_URL'].replace(
            "{{token}}",
            str(response_data.get('url_token'))
        )

        self.assertEqual(
            response_data.get('nb_places_used'),
            0
        )

        self.assertEqual(
            response_data.get('front_url'),
            url
        )
