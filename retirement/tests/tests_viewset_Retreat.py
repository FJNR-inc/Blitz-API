import json
from datetime import datetime, timedelta

import pytz
import responses
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from blitz_api.factories import AdminFactory, UserFactory
from blitz_api.services import remove_translation_fields

from ..models import Retreat

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(RetreatTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.maxDiff = 10000
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
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
        )

        self.retreat2 = Retreat.objects.create(
            name="ultra_retreat",
            details="This is a description of the ultra retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
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
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
        )

        self.retreat_hidden = Retreat.objects.create(
            name="hidden_retreat",
            details="This is a description of the hidden retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2140, 1, 17, 12)),
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
            hidden=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
        )

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create_physical_retreat(self):
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
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'available_on_product_types': [],
            'available_on_products': [],
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_retreat',
            'notification_interval': '1 00:00:00',
            'pictures': [],
            'start_time': '2130-01-15T12:00:00-05:00',
            'end_time': '2130-01-17T16:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'activity_language': None,
            'price': '100.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': True,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'has_shared_rooms': True,
            'options': [],
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['id']
        del response_data['url']

        self.assertEqual(
            response_data,
            content
        )

    @override_settings(
        EXTERNAL_SCHEDULER={
            'URL': "http://example.com",
            'USER': "user",
            'PASSWORD': "password",
        }
    )
    @responses.activate
    def test_create_virtual_retreat(self):
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
            'type': 'V',
            'details': "short_description",
            'timezone': "America/Montreal",
            'price': '100.00',
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': True,
            'hidden': False,
            'description': None,
            'sub_title': None,
            'postal_code': None,
            'place_name': None
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'address_line1': None,
            'address_line2': None,
            'available_on_product_types': [],
            'available_on_products': [],
            'city': None,
            'country': None,
            'postal_code': None,
            'state_province': None,
            'latitude': None,
            'longitude': None,
            'name': 'random_retreat',
            'notification_interval': '1 00:00:00',
            'pictures': [],
            'start_time': '2130-01-15T12:00:00-05:00',
            'end_time': '2130-01-17T16:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'activity_language': None,
            'price': '100.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': True,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'accessibility': None,
            'form_url': None,
            'carpool_url': None,
            'review_url': None,
            'place_name': None,
            'has_shared_rooms': None,
            'options': [],
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': None,
            'room_type': None,
            'type': 'V',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['id']
        del response_data['url']

        self.assertEqual(
            response_data,
            content
        )

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
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'available_on_product_types': [],
            'available_on_products': [],
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_retreat',
            'notification_interval': '1 00:00:00',
            'options': [],
            'pictures': [],
            'start_time': '2130-01-15T12:00:00-05:00',
            'end_time': '2130-01-17T16:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'activity_language': None,
            'price': '100.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': True,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'has_shared_rooms': True,
            'hidden': True,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['id']
        del response_data['url']

        self.assertEqual(
            response_data,
            content
        )

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
        }

        response = self.client.post(
            reverse('retreat:retreat-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'available_on_product_types': [],
            'available_on_products': [],
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_retreat',
            'notification_interval': '1 00:00:00',
            'options': [],
            'pictures': [],
            'start_time': '2130-01-15T12:00:00-05:00',
            'end_time': '2130-01-17T16:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'activity_language': None,
            'price': '100.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': True,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'users': [],
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'has_shared_rooms': True,
            'hidden': True,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': None,
            'room_type': None,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['id']
        del response_data['url']

        self.assertEqual(
            response_data,
            content
        )

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
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 16)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 500,
            'is_active': True,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': False,
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
            'name': "mega_retreat",
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
            'hidden': False,
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
            'details': ['This field is required.'],
            'address_line1': ['This field is required.'],
            'city': ['This field is required.'],
            'country': ['This field is required.'],
            'name': ['This field is required.'],
            'postal_code': ['This field is required.'],
            'seats': ['This field is required.'],
            'state_province': ['This field is required.'],
            'timezone': ['This field is required.'],
            "price": ["This field is required."],
            "start_time": ["This field is required."],
            "end_time": ["This field is required."],
            "min_day_refund": ["This field is required."],
            "refund_rate": ["This field is required."],
            "min_day_exchange": ["This field is required."],
            "is_active": ["This field is required."],
            "accessibility": ["This field is required."],
            "has_shared_rooms": ["This field is required."],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
            'start_time': "",
            'end_time': "",
            'is_active': "",
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
            'is_active': ['Must be a valid boolean.'],
            'end_time': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'price': ['A valid number is required.'],
            'start_time': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'min_day_exchange': ['A valid integer is required.'],
            'min_day_refund': ['A valid integer is required.'],
            'refund_rate': ['A valid integer is required.'],
            'accessibility': ['Must be a valid boolean.'],
            'form_url': ['Not a valid string.'],
            'carpool_url': ['Not a valid string.'],
            'review_url': ['Not a valid string.'],
            'has_shared_rooms': ['Must be a valid boolean.'],
            'place_name': ['Not a valid string.'],
            'type': ['"[1]" is not a valid choice.'],
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
            'start_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            'min_day_refund': 7,
            'min_day_exchange': 7,
            'refund_rate': 50,
            'is_active': False,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'has_shared_rooms': True,
            'hidden': False,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
        }

        response = self.client.put(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
            data,
            format='json',
        )

        content = {
            'details': 'short_description',
            'email_content': None,
            'activity_language': 'FR',
            'id': self.retreat.id,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'New city',
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'New Name',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'seats': 40,
            'reserved_seats': 0,
            'notification_interval': '1 00:00:00',
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': "America/Montreal",
            'is_active': False,
            'places_remaining': 40,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'users': [],
            'url': 'http://testserver/retreat/retreats/' +
                   str(self.retreat.id),
            'has_shared_rooms': True,
            'available_on_product_types': [],
            'available_on_products': [],
            'options': [],
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': True,
            'room_type': Retreat.DOUBLE_OCCUPATION,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a retreat (setting is_active to false).
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

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'activity_language': 'FR',
                    'details': 'This is a description of the mega retreat.',
                    'email_content': None,
                    'id': self.retreat.id,
                    'address_line1': '123 random street',
                    'address_line2': None,
                    'city': None,
                    'country': 'Random country',
                    'postal_code': '123 456',
                    'state_province': 'Random state',
                    'latitude': None,
                    'longitude': None,
                    'name': 'mega_retreat',
                    'pictures': [],
                    'start_time': '2130-01-15T08:00:00-05:00',
                    'end_time': '2130-01-17T12:00:00-05:00',
                    'seats': 400,
                    'reserved_seats': 0,
                    'notification_interval': '1 00:00:00',
                    'price': '199.00',
                    'exclusive_memberships': [],
                    'timezone': None,
                    'is_active': True,
                    'places_remaining': 400,
                    'min_day_exchange': 7,
                    'min_day_refund': 7,
                    'refund_rate': 50,
                    'reservations': [],
                    'reservations_canceled': [],
                    'total_reservations': 0,
                    'accessibility': True,
                    'form_url': "example.com",
                    'carpool_url': 'example2.com',
                    'review_url': 'example3.com',
                    'place_name': None,
                    'users': [],
                    'url': 'http://testserver/retreat/retreats/' +
                           str(self.retreat.id),
                    'has_shared_rooms': True,
                    'available_on_product_types': [],
                    'available_on_products': [],
                    'options': [],
                    'hidden': False,
                    'accessibility_detail': None,
                    'description': None,
                    'food_allergen_free': False,
                    'food_gluten_free': False,
                    'food_vegan': False,
                    'food_vege': False,
                    'google_maps_url': None,
                    'sub_title': None,
                    'toilet_gendered': False,
                    'room_type': Retreat.SINGLE_OCCUPATION,
                    'type': 'P',
                    'videoconference_tool': None,
                    'videoconference_link': None
                }
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_admin(self):
        self.client.force_authenticate(user=self.admin)

        self.retreat2.is_active = False
        self.retreat2.save()

        response = self.client.get(
            reverse('retreat:retreat-list'),
            format='json',
        )

        content = {'count': 3, 'next': None, 'previous': None, 'results': [
            {
                'places_remaining': 400, 'total_reservations': 0,
                'reservations': [], 'reservations_canceled': [],
                'timezone': None,
                'name': 'hidden_retreat', 'name_fr': None,
                'name_en': 'hidden_retreat',
                'details': 'This is a description of the hidden retreat.',
                'country': 'Random country', 'state_province': 'Random state',
                'city': None, 'address_line1': '123 random street',
                'has_shared_rooms': True, 'is_active': True,
                'accessibility': True,
                'pictures': [], 'place_name': None, 'country_fr': None,
                'country_en': 'Random country', 'state_province_fr': None,
                'state_province_en': 'Random state', 'city_fr': None,
                'city_en': None, 'address_line1_fr': None,
                'address_line1_en': '123 random street', 'address_line2': None,
                'address_line2_fr': None, 'address_line2_en': None,
                'available_on_product_types': [],
                'available_on_products': [],
                'postal_code': '123 456', 'latitude': None, 'longitude': None,
                'details_fr': None,
                'details_en': 'This is a description of the hidden retreat.',
                'seats': 400, 'reserved_seats': 0,
                'notification_interval': '1 00:00:00',
                'old_id': None,
                'options': [],
                'activity_language': 'FR',
                'price': '199.00', 'start_time': '2140-01-15T08:00:00-05:00',
                'end_time': '2140-01-17T12:00:00-05:00', 'min_day_refund': 7,
                'refund_rate': 50, 'min_day_exchange': 7,
                'email_content': None,
                'form_url': 'example.com', 'carpool_url': 'example2.com',
                'review_url': 'example3.com', 'hidden': True, 'users': [],
                'exclusive_memberships': [],
                'accessibility_detail': None,
                'description': None,
                'food_allergen_free': False,
                'food_gluten_free': False,
                'food_vegan': False,
                'food_vege': False,
                'google_maps_url': None,
                'sub_title': None,
                'toilet_gendered': False,
                'room_type': Retreat.SINGLE_OCCUPATION,
                'type': 'P',
                'videoconference_tool': None,
                'videoconference_link': None
            },
            {
                'places_remaining': 400, 'total_reservations': 0,
                'reservations': [], 'reservations_canceled': [],
                'timezone': None,
                'name': 'mega_retreat', 'name_fr': None,
                'name_en': 'mega_retreat',
                'details': 'This is a description of the mega retreat.',
                'country': 'Random country', 'state_province': 'Random state',
                'city': None, 'address_line1': '123 random street',
                'has_shared_rooms': True, 'is_active': True,
                'accessibility': True,
                'pictures': [], 'place_name': None, 'country_fr': None,
                'country_en': 'Random country', 'state_province_fr': None,
                'state_province_en': 'Random state', 'city_fr': None,
                'city_en': None, 'address_line1_fr': None,
                'address_line1_en': '123 random street', 'address_line2': None,
                'address_line2_fr': None, 'address_line2_en': None,
                'available_on_product_types': [],
                'available_on_products': [],
                'postal_code': '123 456', 'latitude': None, 'longitude': None,
                'details_fr': None,
                'details_en': 'This is a description of the mega retreat.',
                'seats': 400, 'reserved_seats': 0,
                'notification_interval': '1 00:00:00',
                'old_id': None,
                'options': [],
                'activity_language': 'FR',
                'price': '199.00', 'start_time': '2130-01-15T08:00:00-05:00',
                'end_time': '2130-01-17T12:00:00-05:00', 'min_day_refund': 7,
                'refund_rate': 50, 'min_day_exchange': 7,
                'email_content': None,
                'form_url': 'example.com', 'carpool_url': 'example2.com',
                'review_url': 'example3.com', 'hidden': False, 'users': [],
                'exclusive_memberships': [],
                'accessibility_detail': None,
                'description': None,
                'food_allergen_free': False,
                'food_gluten_free': False,
                'food_vegan': False,
                'food_vege': False,
                'google_maps_url': None,
                'sub_title': None,
                'toilet_gendered': False,
                'room_type': Retreat.SINGLE_OCCUPATION,
                'type': 'P',
                'videoconference_tool': None,
                'videoconference_link': None
            },
            {
                'places_remaining': 400, 'total_reservations': 0,
                'reservations': [], 'reservations_canceled': [],
                'timezone': None,
                'name': 'ultra_retreat', 'name_fr': None,
                'name_en': 'ultra_retreat',
                'details': 'This is a description of the ultra retreat.',
                'country': 'Random country', 'state_province': 'Random state',
                'city': None, 'address_line1': '123 random street',
                'has_shared_rooms': True, 'is_active': False,
                'accessibility': True, 'pictures': [], 'place_name': None,
                'country_fr': None, 'country_en': 'Random country',
                'state_province_fr': None, 'state_province_en': 'Random state',
                'city_fr': None, 'city_en': None, 'address_line1_fr': None,
                'address_line1_en': '123 random street', 'address_line2': None,
                'address_line2_fr': None, 'address_line2_en': None,
                'available_on_product_types': [],
                'available_on_products': [],
                'postal_code': '123 456', 'latitude': None, 'longitude': None,
                'details_fr': None,
                'details_en': 'This is a description of the ultra retreat.',
                'seats': 400, 'reserved_seats': 0,
                'notification_interval': '1 00:00:00',
                'old_id': None,
                'options': [],
                'activity_language': 'FR',
                'price': '199.00', 'start_time': '2140-01-15T08:00:00-05:00',
                'end_time': '2140-01-17T12:00:00-05:00', 'min_day_refund': 7,
                'refund_rate': 50, 'min_day_exchange': 7,
                'email_content': None,
                'form_url': 'example.com', 'carpool_url': 'example2.com',
                'review_url': 'example3.com', 'hidden': False, 'users': [],
                'exclusive_memberships': [],
                'accessibility_detail': None,
                'description': None,
                'food_allergen_free': False,
                'food_gluten_free': False,
                'food_vegan': False,
                'food_vege': False,
                'google_maps_url': None,
                'sub_title': None,
                'toilet_gendered': False,
                'room_type': Retreat.SINGLE_OCCUPATION,
                'type': 'P',
                'videoconference_tool': None,
                'videoconference_link': None
            }]}

        response_content = json.loads(response.content)
        del response_content['results'][0]['url']
        del response_content['results'][0]['id']
        del response_content['results'][1]['url']
        del response_content['results'][1]['id']
        del response_content['results'][2]['url']
        del response_content['results'][2]['id']

        self.assertEqual(response_content, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_filtered_by_end_time_gte(self):
        """
        Ensure we can list retreats filtered by end_time greater
        than a given date.
        """

        response = self.client.get(
            reverse('retreat:retreat-list') +
            "?end_time__gte=2139-01-01T00:00:00",
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'activity_language': 'FR',
                'details': 'This is a description of the ultra retreat.',
                'email_content': None,
                'id': self.retreat2.id,
                'address_line1': '123 random street',
                'address_line2': None,
                'city': None,
                'country': 'Random country',
                'postal_code': '123 456',
                'state_province': 'Random state',
                'latitude': None,
                'longitude': None,
                'name': 'ultra_retreat',
                'pictures': [],
                'start_time': '2140-01-15T08:00:00-05:00',
                'end_time': '2140-01-17T12:00:00-05:00',
                'seats': 400,
                'reserved_seats': 0,
                'notification_interval': '1 00:00:00',
                'price': '199.00',
                'exclusive_memberships': [],
                'timezone': None,
                'is_active': True,
                'places_remaining': 400,
                'min_day_exchange': 7,
                'min_day_refund': 7,
                'refund_rate': 50,
                'reservations': [],
                'reservations_canceled': [],
                'total_reservations': 0,
                'accessibility': True,
                'form_url': "example.com",
                'carpool_url': 'example2.com',
                'review_url': 'example3.com',
                'place_name': None,
                'users': [],
                'url': 'http://testserver/retreat/retreats/' +
                       str(self.retreat2.id),
                'has_shared_rooms': True,
                'available_on_product_types': [],
                'available_on_products': [],
                'options': [],
                'hidden': False,
                'accessibility_detail': None,
                'description': None,
                'food_allergen_free': False,
                'food_gluten_free': False,
                'food_vegan': False,
                'food_vege': False,
                'google_maps_url': None,
                'sub_title': None,
                'toilet_gendered': False,
                'room_type': Retreat.SINGLE_OCCUPATION,
                'type': 'P',
                'videoconference_tool': None,
                'videoconference_link': None
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        content = {
            'details': 'This is a description of the mega retreat.',
            'email_content': None,
            'activity_language': 'FR',
            'id': self.retreat.id,
            'address_line1': '123 random street',
            'address_line2': None,
            'city': None,
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'mega_retreat',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'seats': 400,
            'reserved_seats': 0,
            'notification_interval': '1 00:00:00',
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': None,
            'is_active': True,
            'places_remaining': 400,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'users': [],
            'url': 'http://testserver/retreat/retreats/' +
                   str(self.retreat.id),
            'has_shared_rooms': True,
            'available_on_product_types': [],
            'available_on_products': [],
            'options': [],
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': False,
            'room_type': Retreat.SINGLE_OCCUPATION,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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

        response_data = json.loads(response.content)

        self.assertTrue('name_fr' in response_data)

        response_data = remove_translation_fields(response_data)

        content = {
            'details': 'This is a description of the mega retreat.',
            'activity_language': 'FR',
            'email_content': None,
            'id': self.retreat.id,
            'address_line1': '123 random street',
            'address_line2': None,
            'city': None,
            'country': 'Random country',
            'postal_code': '123 456',
            'state_province': 'Random state',
            'latitude': None,
            'longitude': None,
            'name': 'mega_retreat',
            'pictures': [],
            'start_time': '2130-01-15T08:00:00-05:00',
            'end_time': '2130-01-17T12:00:00-05:00',
            'reserved_seats': 0,
            'notification_interval': '1 00:00:00',
            'seats': 400,
            'price': '199.00',
            'exclusive_memberships': [],
            'timezone': None,
            'is_active': True,
            'places_remaining': 400,
            'min_day_exchange': 7,
            'min_day_refund': 7,
            'refund_rate': 50,
            'reservations': [],
            'reservations_canceled': [],
            'total_reservations': 0,
            'accessibility': True,
            'form_url': "example.com",
            'carpool_url': 'example2.com',
            'review_url': 'example3.com',
            'place_name': None,
            'users': [],
            'url': 'http://testserver/retreat/retreats/' +
                   str(self.retreat.id),
            'has_shared_rooms': True,
            'available_on_product_types': [],
            'available_on_products': [],
            'options': [],
            'hidden': False,
            'accessibility_detail': None,
            'description': None,
            'food_allergen_free': False,
            'food_gluten_free': False,
            'food_vegan': False,
            'food_vege': False,
            'google_maps_url': None,
            'sub_title': None,
            'toilet_gendered': False,
            'room_type': Retreat.SINGLE_OCCUPATION,
            'type': 'P',
            'videoconference_tool': None,
            'videoconference_link': None
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
