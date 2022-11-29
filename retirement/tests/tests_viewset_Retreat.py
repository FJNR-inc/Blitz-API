import json
from unittest.mock import patch
from datetime import (
    datetime,
    timedelta,
)

import pytz
import responses
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from blitz_api.factories import (
    AdminFactory,
    UserFactory,
)
from blitz_api.models import AcademicLevel
from blitz_api.testing_tools import CustomAPITestCase
from store.models import Membership

from retirement.models import (
    Retreat,
    RetreatType,
    RetreatDate,
    Reservation,
)
User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatTests(CustomAPITestCase):
    ATTRIBUTES = [
        'id',
        'url',
        'details',
        'email_content',
        'address_line1',
        'address_line2',
        'available_on_product_types',
        'available_on_products',
        'city',
        'country',
        'postal_code',
        'state_province',
        'latitude',
        'longitude',
        'name',
        'notification_interval',
        'pictures',
        'start_time',
        'end_time',
        'seats',
        'reserved_seats',
        'activity_language',
        'price',
        'exclusive_memberships',
        'timezone',
        'is_active',
        'places_remaining',
        'min_day_exchange',
        'min_day_refund',
        'refund_rate',
        'total_reservations',
        'accessibility',
        'form_url',
        'carpool_url',
        'review_url',
        'place_name',
        'has_shared_rooms',
        'options',
        'hidden',
        'accessibility_detail',
        'description',
        'food_allergen_free',
        'food_gluten_free',
        'food_vegan',
        'food_vege',
        'google_maps_url',
        'sub_title',
        'toilet_gendered',
        'room_type',
        'type',
        'videoconference_tool',
        'videoconference_link',
        'dates',
        'number_of_tomatoes',
        'animator',
        'display_start_time',
        'hide_from_client_admin_panel',
        'require_purchase_room',
        'available_on_retreat_types',
        'is_specific_to_community',
        'community_description',
        'community_name',
    ]

    @classmethod
    def setUpClass(cls):
        super(RetreatTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.maxDiff = 10000
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()

        self.retreat2 = Retreat.objects.create(
            name="ultra retreat",
            details="This is a description of the ultra retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2140, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
            retreat=self.retreat2,
        )
        self.retreat2.activate()

        self.retreat_hidden = Retreat.objects.create(
            name="hidden_retreat",
            details="This is a description of the hidden retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            hidden=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2140, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
            retreat=self.retreat_hidden,
        )
        self.retreat_hidden.activate()

        self.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        self.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            price=50,
            available=True,
            duration=timedelta(days=365),
        )

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create_retreat(self):
        """
        Ensure we can create a retreat if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/authentication",
            json={"token": "1234567890"},
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/tasks",
            status=200
        )

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'hidden': False,
            'description': None,
            'sub_title': None,
            'postal_code': None,
            'place_name': None,
            "display_start_time": LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 12),
            ),
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        content = json.loads(response.content)
        self.check_attributes(content, attributes)

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create(self):
        """
        Ensure we can create a retreat if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/authentication",
            json={"token": "1234567890"},
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/tasks",
            status=200
        )

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': True,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': True,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
            'display_start_time': LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 12),
            ),
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        content = json.loads(response.content)
        self.check_attributes(content, attributes)

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create_batch_retreat_with_missing_field(self):
        """
        Ensure we can't create a batch retreat without bulk date.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/authentication",
            json={"token": "1234567890"},
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/tasks",
            status=200
        )

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'hidden': False,
            'description': None,
            'sub_title': None,
            'postal_code': None,
            'place_name': None,
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-batch-create'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        content = json.loads(response.content)

        self.assertEqual(
            content,
            {
                "bulk_start_time": ["This field is required."],
                "bulk_end_time": ["This field is required."],
                "weekdays": ["This field is required."]
            }
        )

    @responses.activate
    def test_create_batch_retreat(self):
        """
        Ensure we can create a batch of retreat if everything is perfect.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/authentication",
            json={"token": "1234567890"},
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/tasks",
            status=200
        )

        data = {
            'seats': 40,
            'details': "short_description",
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'hidden': False,
            'description': None,
            'sub_title': None,
            'postal_code': None,
            'place_name': None,
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
            'exclusive_memberships': [
                reverse(
                    'membership-detail',
                    args=[self.membership.id]
                )
            ],
            'bulk_start_time': '2021-03-01T08:00:00Z',
            'bulk_end_time': '2021-03-30T12:00:00Z',
            'weekdays': [0, 1, 2]
        }

        response = self.client.post(
            reverse('retreat:retreat-batch-create'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = json.loads(response.content)

        self.assertEqual(
            len(content),
            14,
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]

        for item in content:
            self.assertEqual(item['name'][-2:], 'AM', item)
            self.assertEqual(
                item['exclusive_memberships'],
                [
                    'http://testserver' + reverse(
                        'membership-detail',
                        args=[self.membership.id]
                    )
                ],
            )
            self.check_attributes(item, attributes)

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create_without_toilet_gendered_and_room_type(self):
        """
        Ensure we can create a retreat if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/authentication",
            json={"token": "1234567890"},
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/tasks",
            status=200
        )

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': True,
            "display_start_time": LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 12),
            ),
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        content = json.loads(response.content)
        self.check_attributes(content, attributes)

    def test_create_invalid_refund_rate(self):
        """
        Ensure we can't create a retreat if refund_rate is not between
        0 and 100%.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 500,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': False,
            'display_start_time': LOCAL_TIMEZONE.localize(
                datetime(2140, 1, 15, 8)
            ),
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        content = {
            'refund_rate': [
                'Refund rate must be between 0 and 100 (%).'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_without_permission(self):
        """
        Ensure we can't create a retreat if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_retreat",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal"
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_duplicate_name(self):
        """
        Ensure we can't create a retreat with same name.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': self.retreat.name,
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'price': '100.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': False,
            'display_start_time': LOCAL_TIMEZONE.localize(
                datetime(2140, 1, 15, 8)
            ),
            'type': reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType.id]
            ),
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        content = {'name': ['This field must be unique.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a retreat when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = dict()

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        content = {
            "price": ["This field is required."],
            "timezone": ["This field is required."],
            "display_start_time": ["This field is required."],
            "type": ["This field is required."],
            "name": ["This field is required."],
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        self.assertEqual(
            json.loads(response.content),
            content,
            response.content
        )

    def test_create_invalid_field(self):
        """
        Ensure we can't create a retreat with invalid fields.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': ("invalid",),
            'seats': "invalid",
            'activity_language': (1,),
            'details': ("invalid",),
            'postal_code': (1,),
            'city': (1,),
            'address_line1': (1,),
            'country': (1,),
            'state_province': (1,),
            'timezone': ("invalid",),
            'price': "",
            'min_day_exchange': (1,),
            'min_day_refund': (1,),
            'refund_rate': (1,),
            'accessibility': (1,),
            'form_url': (1,),
            'carpool_url': (1,),
            'review_url': (1,),
            'place_name': (1,),
            'has_shared_rooms': (1, ),
            'hidden': False,
            'type': (1,),
            'display_start_time': (1,),
            'videoconference_tool': (1, )
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        content = {
            'activity_language': ['"[1]" is not a valid choice.'],
            'details': ['Not a valid string.'],
            'name': ['Not a valid string.'],
            'city': ['Not a valid string.'],
            'address_line1': ['Not a valid string.'],
            'postal_code': ['Not a valid string.'],
            'state_province': ['Not a valid string.'],
            'country': ['Not a valid string.'],
            'seats': ['A valid integer is required.'],
            'timezone': ['Unknown timezone'],
            'price': ['A valid number is required.'],
            'min_day_exchange': ['A valid integer is required.'],
            'min_day_refund': ['A valid integer is required.'],
            'refund_rate': ['A valid integer is required.'],
            'accessibility': ['Must be a valid boolean.'],
            'form_url': ['Not a valid string.'],
            'carpool_url': ['Not a valid string.'],
            'review_url': ['Not a valid string.'],
            'has_shared_rooms': ['Must be a valid boolean.'],
            'place_name': ['Not a valid string.'],
            'type': ['Incorrect type. Expected URL string, received list.'],
            'display_start_time': [
                'Datetime has wrong format. Use one of these formats '
                'instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'videoconference_tool': ['Not a valid string.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a retreat.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "New Name",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'New city',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'timezone': "America/Montreal",
            'price': '199.00',
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': False,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
        }

        response = self.client.patch(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        content = json.loads(response.content)
        self.check_attributes(content, attributes)

    def test_edit_community_info(self):
        """
        Ensure we can update community info of a retreat.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': self.retreat.name,
            'is_specific_to_community': True,
            'community_description': 'Lorem ipsum communities',
            'community_name': 'My new community',
        }

        response = self.client.patch(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        content = json.loads(response.content)
        self.check_attributes(content, attributes)

        self.assertEqual(
            content['is_specific_to_community'],
            data['is_specific_to_community'],
        )
        self.assertEqual(
            content['community_description'],
            data['community_description'],
        )
        self.assertEqual(
            content['community_name'],
            data['community_name'],
        )

    def test_delete_without_participants(self):
        """
        Ensure we can delete a retreat (setting is_active to false).
        without participants
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content,
        )

        self.retreat.refresh_from_db()
        self.assertFalse(self.retreat.is_active)
        self.assertTrue(self.retreat.hide_from_client_admin_panel)

        self.retreat.is_active = True

    def test_delete_with_participants_no_message(self):
        """
        Ensure we can't delete a retreat that has participants
        without a message.
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )

        response = self.client.delete(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_deleted_retreat_email')
    def test_delete_with_participants(self, mock_email, mock_cancel):
        """
        Ensure we can delete a retreat that has participants
        """
        self.client.force_authenticate(user=self.admin)
        deletion_message = 'No more fun.'

        user = UserFactory()
        user2 = UserFactory()

        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        Reservation.objects.create(
            user=user2,
            retreat=self.retreat,
            is_active=True,
        )

        response = self.client.delete(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
            {
                'deletion_message': deletion_message
            }
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content,
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            deletion_message
        )
        mock_cancel.assert_called_once_with(False)

        self.retreat.refresh_from_db()
        self.assertFalse(self.retreat.is_active)
        self.assertTrue(self.retreat.hide_from_client_admin_panel)

        self.retreat.is_active = True

    def test_list(self):
        """
        Ensure we can list retreats as an unauthenticated user.
        Only if retreat is_active == True.
        """

        self.retreat2.is_active = False
        self.retreat2.save()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['results']), 1)

        for item in content['results']:
            self.check_attributes(item)

    def test_list_with_search(self):
        """
        Ensure we can list retreats with a search by name
        """
        self.client.force_authenticate(user=self.admin)

        self.retreat2.is_active = False
        self.retreat2.save()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'search': 'mega'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(content['results']), 1)

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        for item in content['results']:
            self.check_attributes(item, attributes)

    def test_list_as_admin(self):
        self.client.force_authenticate(user=self.admin)

        self.retreat2.is_active = False
        self.retreat2.save()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        for item in content['results']:
            self.check_attributes(item, attributes)

    def test_read(self):
        """
        Ensure we can read a retreat as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = json.loads(response.content)
        self.check_attributes(content)

    def test_read_as_admin(self):
        """
        Ensure we can read a retreat as an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        )

        content = json.loads(response.content)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )
        attributes = self.ATTRIBUTES + [
            'state_province_fr',
            'old_id',
            'details_en',
            'details_fr',
            'address_line2_en',
            'name_en',
            'name_fr',
            'state_province_en',
            'country_fr',
            'country_en',
            'city_en',
            'address_line2_fr',
            'address_line1_fr',
            'city_fr',
            'address_line1_en',
        ]
        self.check_attributes(content, attributes)

    def test_read_non_existent_retreat(self):
        """
        Ensure we get not found when asking for a retreat that doesn't
        exist.
        """

        response = self.client.get(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reminder_email(self):
        """
        Ensure emails are sent to every user that has a reservation to the
        targeted retreat.
        """

        with mock.patch(
                'retirement.views.timezone.now',
                return_value=self.retreat.start_time):
            response = self.client.get(
                reverse(
                    'retreat:retreat-remind-users',
                    kwargs={'pk': self.retreat.id},
                ),
            )

        content = {
            'stop': True,
            'emails': [],  # No reservation on this retreat
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            len(mail.outbox),
            self.retreat.reservations.filter(is_active=True).count()
        )

    def test_batch_activate_retreat_invalid_ids(self):
        """
        Ensure we can activate multiple retreat with one call.
        """
        self.client.force_authenticate(user=self.admin)

        retreat = Retreat.objects.create(
            name="mega retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )

        # Two IDs does not exist in this data
        data = {
            'retreats': [997, 998, retreat.id],
        }

        response = self.client.post(
            reverse('retreat:retreat-batch-activate'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            response.json(),
            {
                'retreat_ids': [
                    'These retreats does not exist: [997, 998]'
                ]
            }
        )

    def test_batch_activate_retreat_error_on_activation(self):
        """
        Ensure we can activate multiple retreat with one call.
        """
        self.client.force_authenticate(user=self.admin)

        retreat = Retreat.objects.create(
            name="mega retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )

        # Two IDs does not exist in this data
        data = {
            'retreats': [retreat.id],
        }

        response = self.client.post(
            reverse('retreat:retreat-batch-activate'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(
            response.json(),
            {
                "retreat": retreat.id,
                "non_field_errors": [
                    "Retreat need to have a start time before activate it"
                ]
            }
        )

    def test_batch_activate_retreat(self):
        """
        Ensure we can activate multiple retreat with one call.
        """
        self.client.force_authenticate(user=self.admin)

        retreat = Retreat.objects.create(
            name="mega retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            activity_language='FR',
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=retreat,
        )

        # Two IDs does not exist in this data
        data = {
            'retreats': [retreat.id],
        }

        response = self.client.post(
            reverse('retreat:retreat-batch-activate'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(
            response.content,
            b'',
        )

    def test_reminder_email_too_early(self):
        """
        Ensure we can't send emails too early. Prevents spamming by anonymous
        users.
        """
        FIXED_TIME = self.retreat.start_time - timedelta(days=9)

        with mock.patch(
                'retirement.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.get(
                reverse(
                    'retreat:retreat-remind-users',
                    kwargs={'pk': self.retreat.id},
                ),
            )

        content = {'detail': "Retreat takes place in more than 8 days."}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(mail.outbox), 0)

    def test_recap_email(self):
        """
        Ensure emails are sent to every user that has a reservation to the
        targeted retreat.
        """

        with mock.patch(
                'retirement.views.timezone.now',
                return_value=self.retreat.end_time):
            response = self.client.get(
                reverse(
                    'retreat:retreat-recap',
                    kwargs={'pk': self.retreat.id},
                ),
            )

        content = {
            'stop': True,
            'emails': [],  # No reservation on this retreat
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            len(mail.outbox),
            self.retreat.reservations.filter(is_active=True).count()
        )

    def test_recap_email_too_early(self):
        """
        Ensure we can't send emails too early. Prevents spamming by anonymous
        users.
        """
        FIXED_TIME = self.retreat.end_time - timedelta(days=2)

        with mock.patch(
                'retirement.views.timezone.now', return_value=FIXED_TIME):
            response = self.client.get(
                reverse(
                    'retreat:retreat-recap',
                    kwargs={'pk': self.retreat.id},
                ),
            )

        content = {'detail': "Retreat ends in more than 1 day."}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(mail.outbox), 0)

    def test_list_retreat_not_finished(self):
        """
        Ensure we can filter by end date and start date of retreats
        """
        self.retreat.delete()
        self.retreat2.delete()
        self.retreat_hidden.delete()

        retreat_finished = Retreat.objects.create(
            name="retreat_finished",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-01T00:00:00Z',
            end_time='2099-01-02T00:00:00Z',
            retreat=retreat_finished,
        )
        retreat_finished.activate()

        retreat_not_finished = Retreat.objects.create(
            name="retreat_not_finished",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2101, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2101-01-01T00:00:00Z',
            end_time='2101-01-02T00:00:00Z',
            retreat=retreat_not_finished,
        )
        retreat_not_finished.activate()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'finish_after': '2100-01-01T00:00:00Z',
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()

        results = content.get('results')

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0].get('id'),
            retreat_not_finished.id
        )

    def test_list_retreat_not_started(self):
        """
        Ensure we can filter by end date and start date of retreats
        """
        self.retreat.delete()
        self.retreat2.delete()
        self.retreat_hidden.delete()

        retreat_started = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-01T00:00:00Z',
            end_time='2099-01-02T00:00:00Z',
            retreat=retreat_started,
        )
        retreat_started.activate()

        retreat_not_started = Retreat.objects.create(
            name="retreat_not_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2101, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2101-01-01T00:00:00Z',
            end_time='2101-01-02T00:00:00Z',
            retreat=retreat_not_started,
        )
        retreat_not_started.activate()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'start_after': '2100-01-01T00:00:00Z',
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()

        results = content.get('results')

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0].get('id'),
            retreat_not_started.id
        )

    def test_list_by_type(self):
        """
        Ensure we can filter by end date and start date of retreats
        """
        Retreat.objects.all().delete()

        retreat_type_2 = RetreatType.objects.create(
            name="Type 2",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )

        retreat_2 = Retreat.objects.create(
            name="retreat_type_2",
            price=199,
            type=retreat_type_2,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-01T00:00:00Z',
            end_time='2099-01-02T00:00:00Z',
            retreat=retreat_2,
        )
        retreat_2.activate()

        retreat_1 = Retreat.objects.create(
            name="retreat_not_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2101, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2101-01-01T00:00:00Z',
            end_time='2101-01-02T00:00:00Z',
            retreat=retreat_1,
        )
        retreat_1.activate()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'type': retreat_type_2.id,
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()

        results = content.get('results')

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0].get('id'),
            retreat_2.id
        )
        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'type__id': retreat_type_2.id,
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()

        results = content.get('results')

        self.assertEqual(len(results), 1)

        self.assertEqual(
            results[0].get('id'),
            retreat_2.id
        )

    def test_list_by_date_interval(self):
        """
        Ensure we can filter by end date and start date of retreats
        """
        Retreat.objects.all().delete()

        retreat_1 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 3),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-03T00:00:00Z',
            end_time='2099-04-01T00:00:00Z',
            retreat=retreat_1,
        )
        RetreatDate.objects.create(
            start_time='2099-04-01T00:00:00Z',
            end_time='2099-04-20T00:00:00Z',
            retreat=retreat_1,
        )
        RetreatDate.objects.create(
            start_time='2099-05-01T00:00:00Z',
            end_time='2099-06-01T00:00:00Z',
            retreat=retreat_1,
        )
        retreat_1.activate()

        retreat_2 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-01T00:00:00Z',
            end_time='2099-02-01T00:00:00Z',
            retreat=retreat_2,
        )
        RetreatDate.objects.create(
            start_time='2099-03-23T00:00:00Z',
            end_time='2099-04-20T00:00:00Z',
            retreat=retreat_2,
        )
        RetreatDate.objects.create(
            start_time='2099-05-20T00:00:00Z',
            end_time='2099-06-01T00:00:00Z',
            retreat=retreat_2,
        )
        retreat_2.activate()

        retreat_3 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 2),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-02T00:00:00Z',
            end_time='2099-06-01T00:00:00Z',
            retreat=retreat_3,
        )
        retreat_3.activate()

        retreat_4 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 1, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-01-04T00:00:00Z',
            end_time='2099-01-05T00:00:00Z',
            retreat=retreat_4,
        )
        RetreatDate.objects.create(
            start_time='2099-01-03T00:00:00Z',
            end_time='2099-01-04T00:00:00Z',
            retreat=retreat_4,
        )
        retreat_4.activate()

        retreat_5 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 6, 1),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-06-01T00:00:00Z',
            end_time='2099-06-02T00:00:00Z',
            retreat=retreat_5,
        )
        RetreatDate.objects.create(
            start_time='2099-06-03T00:00:00Z',
            end_time='2099-06-04T00:00:00Z',
            retreat=retreat_5,
        )
        retreat_5.activate()

        retreat_6 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 3, 10),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-03-10T00:00:00Z',
            end_time='2099-03-11T00:00:00Z',
            retreat=retreat_6,
        )
        RetreatDate.objects.create(
            start_time='2099-04-03T00:00:00Z',
            end_time='2099-04-04T00:00:00Z',
            retreat=retreat_6,
        )
        retreat_6.activate()

        retreat_7 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 2, 10),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-02-10T00:00:00Z',
            end_time='2099-03-11T00:00:00Z',
            retreat=retreat_7,
        )
        RetreatDate.objects.create(
            start_time='2099-04-03T00:00:00Z',
            end_time='2099-04-04T00:00:00Z',
            retreat=retreat_7,
        )
        retreat_7.activate()

        retreat_8 = Retreat.objects.create(
            name="retreat_started",
            price=199,
            type=self.retreatType,
            seats=2,
            min_day_refund=2,
            min_day_exchange=2,
            refund_rate=20,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2099, 3, 11),
            ),
        )
        RetreatDate.objects.create(
            start_time='2099-03-11T00:00:00Z',
            end_time='2099-03-12T00:00:00Z',
            retreat=retreat_8,
        )
        RetreatDate.objects.create(
            start_time='2099-06-03T00:00:00Z',
            end_time='2099-06-04T00:00:00Z',
            retreat=retreat_8,
        )
        retreat_8.activate()

        # Interval
        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'ordering': '-display_start_time',
                'finish_after': '2099-03-01T00:00:00Z',
                'start_before': '2099-05-01T00:00:00Z',
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()
        results = content.get('results')
        id_results = [x['id'] for x in results]
        self.assertEqual(len(results), 6)
        self.assertTrue(retreat_1.id in id_results)
        self.assertTrue(retreat_2.id in id_results)
        self.assertTrue(retreat_3.id in id_results)
        self.assertTrue(retreat_6.id in id_results)
        self.assertTrue(retreat_7.id in id_results)
        self.assertTrue(retreat_8.id in id_results)

        self.assertEqual(results[5].get('id'), retreat_2.id)
        self.assertEqual(results[4].get('id'), retreat_3.id)
        self.assertEqual(results[3].get('id'), retreat_1.id)
        self.assertEqual(results[2].get('id'), retreat_7.id)
        self.assertEqual(results[1].get('id'), retreat_6.id)
        self.assertEqual(results[0].get('id'), retreat_8.id)

        # Hide past retreat
        response = self.client.get(
            reverse('retreat:retreat-list'),
            {
                'ordering': '-display_start_time',
                'finish_after': '2099-05-01T00:00:00Z',
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = response.json()
        results = content.get('results')
        self.assertEqual(len(results), 5)
        id_results = [x['id'] for x in results]
        self.assertTrue(retreat_1.id in id_results)
        self.assertTrue(retreat_2.id in id_results)
        self.assertTrue(retreat_3.id in id_results)
        self.assertTrue(retreat_5.id in id_results)
        self.assertTrue(retreat_8.id in id_results)

        self.assertEqual(results[4].get('id'), retreat_2.id)
        self.assertEqual(results[3].get('id'), retreat_3.id)
        self.assertEqual(results[2].get('id'), retreat_1.id)
        self.assertEqual(results[1].get('id'), retreat_8.id)
        self.assertEqual(results[0].get('id'), retreat_5.id)
