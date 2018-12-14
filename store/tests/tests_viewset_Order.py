import json

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.utils import timezone
from django.urls import reverse

import pytz
import responses
from unittest import mock

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.models import AcademicLevel

from workplace.models import TimeSlot, Period, Workplace
from retirement.models import Retirement

from .paysafe_sample_responses import (SAMPLE_PROFILE_RESPONSE,
                                       SAMPLE_PAYMENT_RESPONSE,
                                       SAMPLE_CARD_RESPONSE,
                                       SAMPLE_INVALID_PAYMENT_TOKEN,
                                       SAMPLE_INVALID_SINGLE_USE_TOKEN,
                                       SAMPLE_CARD_ALREADY_EXISTS,
                                       SAMPLE_CARD_REFUSED,)


from ..models import Package, Order, OrderLine, Membership, PaymentProfile

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(
    PAYSAFE={
        'ACCOUNT_NUMBER': "0123456789",
        'USER': "user",
        'PASSWORD': "password",
        'BASE_URL': "http://example.com/",
        'VAULT_URL': "customervault/v1/",
        'CARD_URL': "cardpayments/v1/"
    }
)
class OrderTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.order_admin = Order.objects.create(
            user=cls.admin,
            transaction_date=timezone.now(),
            authorization_id=2,
            settlement_id=2,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=1,
        )
        cls.payment_profile = PaymentProfile.objects.create(
            name="payment_api_name",
            owner=cls.admin,
            external_api_id="123",
            external_api_url="https://example.com/customervault/v1/profiles"
        )
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.workplace_no_seats = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=0,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.period = Period.objects.create(
            name="random_period_active",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.period_no_seats = Period.objects.create(
            name="random_period_active",
            workplace=cls.workplace_no_seats,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.time_slot = TimeSlot.objects.create(
            name="morning_time_slot",
            period=cls.period,
            price=1,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        cls.time_slot_no_seats = TimeSlot.objects.create(
            name="no_place_left_timeslot",
            period=cls.period_no_seats,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        cls.retirement = Retirement.objects.create(
            name="mega_retirement",
            seats=400,
            details="This is a description of the mega retirement.",
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
        )
        cls.retirement_no_seats = Retirement.objects.create(
            name="no_place_left_retirement",
            seats=0,
            details="This is a description of the full retirement.",
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
        )

    @responses.activate
    def test_create_with_payment_token(self):
        """
        Ensure we can create an order when provided with a payment_token.
        (Token representing an existing payment card.)
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'retirement',
                'object_id': 1,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'id': 3,
            'order_lines': [{
                'content_type': 'membership',
                'id': 2,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/2'
            }, {
                'content_type': 'package',
                'id': 3,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 2,
                'url': 'http://testserver/order_lines/3'
            }, {
                'content_type': 'timeslot',
                'id': 4,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/4'
            }, {
                'content_type': 'retirement',
                'id': 5,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'url': 'http://testserver/order_lines/5',
                'quantity': 1
            }],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/2',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, self.package.reservations * 2)
        self.assertEqual(admin.membership, self.membership)
        self.assertEqual(
            admin.membership_end,
            FIXED_TIME.date() + self.membership.duration
        )
        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_reservation_only(self):
        """
        Ensure we can create an order for a reservation only.
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': 1,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'id': 3,
            'order_lines': [{
                'content_type': 'timeslot',
                'id': 2,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/2'
            }],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/2',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '0',
            'settlement_id': '0',
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 0)
        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_user_has_membership(self):
        """
        Ensure we can't create an order containing a membership if the user
        already has a membership.
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You already have an active membership."
            ]
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_no_place_left(self):
        """
        Ensure we can't create an order with reservations if the requested
        timeslot has no place left.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested timeslot."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_no_place_left_retirement(self):
        """
        Ensure we can't create an order with reservations if the requested
        retirement has no place left.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }, {
                'content_type': 'retirement',
                'object_id': self.retirement_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested retirement."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_not_enough_tickets(self):
        """
        Ensure we can't create an order with reservations if the requesting
        user doesn't have enough tickets.
        """
        self.client.force_authenticate(user=self.admin)

        self.admin.tickets = 0
        self.admin.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You don't have enough tickets to make this reservation."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 0)
        self.assertEqual(admin.membership, None)

        self.admin.tickets = 1
        self.admin.save()

    @responses.activate
    def test_create_with_invalid_payment_token(self):
        """
        Ensure we can't create an order when provided with a bad payment_token.
        (Token representing an non-existing payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )

        data = {
            'payment_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'message': "An error occured while processing the payment: "
                       "invalid payment token or payment profile/card "
                       "inactive."
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_with_single_use_token_no_profile(self):
        """
        Ensure we can create an order when provided with a single_use_token.
        (Token representing a new payment card.)
        The PaymentProfile will be created if none exists.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'order_lines': [{
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': 1,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'id': 3,
            'order_lines': [{
                'content_type': 'package',
                'id': 2,
                'object_id': 1,
                'quantity': 2,
                'url': 'http://testserver/order_lines/2',
                'order': 'http://testserver/orders/3',
            }, {
                'content_type': 'timeslot',
                'id': 3,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/3'
            }],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/1',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
        }

        self.assertEqual(response_data, content)

        user = self.user
        user.refresh_from_db()
        self.assertEqual(user.tickets, self.package.reservations * 2)
        user.tickets = 1
        user.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_with_single_use_token_existing_profile(self):
        """
        Ensure we can create an order when provided with a single_use_token.
        The existing PaymentProfile will be used. A new card will be added.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'id': 3,
            'order_lines': [{
                'content_type': 'membership',
                'id': 2,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/2'
            }, {
                'content_type': 'package',
                'id': 3,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 2,
                'url': 'http://testserver/order_lines/3'
            }],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/2',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
        }

        self.assertEqual(json.loads(response.content), content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, self.package.reservations * 2 + 1)
        self.assertEqual(admin.membership, self.membership)
        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_with_invalid_single_use_token(self):
        """
        Ensure we can't create an order when provided with a bad
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_INVALID_SINGLE_USE_TOKEN,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = content = {
            'message': "An error occured while processing the payment: "
                       "invalid payment or single-use token."
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_with_invalid_single_use_token_no_profile(self):
        """
        Ensure we can't create an order when provided with a bad
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_INVALID_SINGLE_USE_TOKEN,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = content = {
            'message': "An error occured while processing the payment: "
                       "invalid payment or single-use token."
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 1)
        self.assertEqual(user.membership, None)

    @responses.activate
    def test_create_payment_issue(self):
        """
        Ensure we can't create an order when the payment proccessing fails.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_CARD_REFUSED,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': 1,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = content = {
            'message': "An error occured while processing the payment: "
                       "the request has been declined by the issuing bank."
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 1)
        self.assertEqual(user.membership, None)

    @responses.activate
    def test_create_with_single_use_token_existing_card(self):
        """
        Ensure we can create an order when provided with a single_use_token
        representing a card that is already stored in the user's profile.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_ALREADY_EXISTS,
            status=400
        )

        responses.add(
            responses.GET,
            "http://example.com/customervault/v1/cards/456",
            json=SAMPLE_CARD_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'user': reverse('user-detail', args=[self.admin.id]),
            'single_use_token': "invalid",
            'transaction_date': timezone.now(),
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }, {
                'content_type': 'package',
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 2,
                'url': 'http://testserver/order_lines/1'
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'authorization_id': '1',
            'id': 3,
            'order_lines': [{
                'content_type': 'membership',
                'id': 2,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/2'
            }, {
                'content_type': 'package',
                'id': 3,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 2,
                'url': 'http://testserver/order_lines/3'
            }],
            'settlement_id': '1',
            'transaction_date': response_data['transaction_date'],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, self.package.reservations * 2 + 1)
        self.assertEqual(admin.membership, self.membership)

        admin.tickets = 1
        admin.membership = None
        admin.save()

    def test_create_missing_payment_details(self):
        """
        Ensure we can't create an order if no payment details are provided.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': reverse('user-detail', args=[self.user.id]),
            'transaction_date': timezone.now(),
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }, {
                'content_type': 'package',
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 2,
                'url': 'http://testserver/order_lines/1'
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'A payment_token or single_use_token is required to '
                'create an order.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_missing_field(self):
        """
        Ensure we can't create an order when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create an order when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': None,
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create an order when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': (1,),
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': [{
                'non_field_errors': [
                    'Invalid data. Expected a dictionary, but got int.'
                ]
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update an order.
        An empty 'order_lines' list will be ignored.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': [{
                'content_type': 'package',
                'object_id': 1,
                'quantity': 99,
            }],
        }

        response = self.client.put(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'id': 1,
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 99,
                'url': 'http://testserver/order_lines/1'
            }]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete an order.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can't list orders as an unauthenticated user.
        """
        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_owner(self):
        """
        Ensure we can list owned orders as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'order_lines': [{
                    'content_type': 'package',
                    'id': 1,
                    'object_id': 1,
                    'order': 'http://testserver/orders/1',
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/1'
                }],
                'url': 'http://testserver/orders/1',
                'user': 'http://testserver/users/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_admin(self):
        """
        Ensure we can list all orders as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'order_lines': [{
                    'content_type': 'package',
                    'id': 1,
                    'object_id': 1,
                    'order': 'http://testserver/orders/1',
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/1'
                }],
                'url': 'http://testserver/orders/1',
                'user': 'http://testserver/users/1'
            }, {
                'id': 2,
                'transaction_date': data['results'][1]['transaction_date'],
                'authorization_id': '2',
                'settlement_id': '2',
                'order_lines': [],
                'url': 'http://testserver/orders/2',
                'user': 'http://testserver/users/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can't read an order as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_owner(self):
        """
        Ensure we can read an order owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }],
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_owner_not_owned(self):
        """
        Ensure we can't read an order not owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure we can read any order as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }],
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for an order that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
