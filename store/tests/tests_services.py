import json

import pytz
import responses
from django.conf import settings

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from datetime import datetime, timedelta

from blitz_api.factories import UserFactory

from .paysafe_sample_responses import (
    UNKNOWN_EXCEPTION,
    SAMPLE_INVALID_PAYMENT_TOKEN,
    SAMPLE_PROFILE_RESPONSE,
)

from ..exceptions import PaymentAPIError
from ..models import PaymentProfile, Order, Coupon, Package, OrderLine
from ..services import (
    charge_payment,
    get_external_payment_profile,
    create_external_payment_profile,
    update_external_card,
    delete_external_card,
    create_external_card,
    validate_coupon_for_order,
)

User = get_user_model()
LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

PAYMENT_TOKEN = "CIgbMO3P1j7HUiy"
SINGLE_USE_TOKEN = "ASDG3e3gs3vrBTR"


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
class ServicesTests(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.payment_profile = PaymentProfile.objects.create(
            name="Test profile",
            owner=self.user,
            external_api_id="123",
            external_api_url="https://api.test.paysafe.com/customervault/v1/"
                             "profiles/",
        )

        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
            reference_number=751,
        )

        self.coupon = Coupon.objects.create(
            value=13,
            code="ABCDEFGH",
            start_time=LOCAL_TIMEZONE.localize(
                datetime.now() -
                timedelta(weeks=5)
            ),
            end_time=LOCAL_TIMEZONE.localize(
                datetime.now() +
                timedelta(weeks=5)
            ),
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=self.user,
        )
        self.package_type = ContentType.objects.get_for_model(Package)
        self.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=600,
            reservations=100,
        )
        self.package_2 = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        self.package_most_exp_product = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=9999,
            reservations=100,
        )
        self.package_less_exp_product = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=1,
            reservations=100,
        )
        self.coupon.applicable_product_types.add(self.package_type)

        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package.id,
            cost=self.package.price,
        )
        self.order_line_2 = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package_2.id,
            cost=self.package_2.price,
        )

    @responses.activate
    def test_get_external_payment_profile(self):
        """
        Ensure we can get a user's external payment profile.
        """
        responses.add(
            responses.GET,
            "http://example.com/customervault/v1/profiles/123?fields=cards",
            json=SAMPLE_PROFILE_RESPONSE,
            status=200
        )

        response = get_external_payment_profile(
            self.payment_profile.external_api_id
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), SAMPLE_PROFILE_RESPONSE)

    @responses.activate
    def test_create_external_payment_profile(self):
        """
        Ensure we can create a user's external payment profile.
        """
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=201
        )
        response = create_external_payment_profile(self.user)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content), SAMPLE_PROFILE_RESPONSE)

    @responses.activate
    def test_update_external_card(self):
        """
        Ensure we can update a user's card.
        """
        responses.add(
            responses.PUT,
            "http://example.com/customervault/v1/profiles/123/cards/456",
            json=SAMPLE_PROFILE_RESPONSE,
            status=200
        )
        response = update_external_card(
            self.payment_profile.external_api_id,
            SAMPLE_PROFILE_RESPONSE['cards'][0]['id'],
            SINGLE_USE_TOKEN,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), SAMPLE_PROFILE_RESPONSE)

    @responses.activate
    def test_delete_external_card(self):
        """
        Ensure we can delete a user's card.
        """
        responses.add(
            responses.DELETE,
            "http://example.com/customervault/v1/profiles/123/cards/456",
            json='',
            status=204
        )
        response = delete_external_card(
            self.payment_profile.external_api_id,
            SAMPLE_PROFILE_RESPONSE['cards'][0]['id'],
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @responses.activate
    def test_create_external_card(self):
        """
        Ensure we can create a new card for a user.
        """
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=200
        )
        response = create_external_card(
            self.payment_profile.external_api_id,
            SINGLE_USE_TOKEN,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), SAMPLE_PROFILE_RESPONSE)

    @responses.activate
    def test_charge_payment(self):
        """
        Ensure we can charge a user.
        """
        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=200
        )
        response = charge_payment(1000, PAYMENT_TOKEN, "123")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), SAMPLE_PROFILE_RESPONSE)

    @responses.activate
    def test_unknown_external_api_exception(self):
        """
        Ensure we catch unhandled errors of the external API.
        """
        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=UNKNOWN_EXCEPTION,
            status=400
        )
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=UNKNOWN_EXCEPTION,
            status=400
        )
        responses.add(
            responses.PUT,
            "http://example.com/customervault/v1/profiles/123/cards/456",
            json=UNKNOWN_EXCEPTION,
            status=400
        )
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=UNKNOWN_EXCEPTION,
            status=400
        )
        responses.add(
            responses.GET,
            "http://example.com/customervault/v1/profiles/123?fields=cards",
            json=UNKNOWN_EXCEPTION,
            status=400
        )
        self.assertRaises(
            PaymentAPIError,
            charge_payment,
            1000,
            PAYMENT_TOKEN,
            "123"
        )
        self.assertRaises(
            PaymentAPIError,
            create_external_card,
            self.payment_profile.external_api_id,
            SINGLE_USE_TOKEN
        )
        self.assertRaises(
            PaymentAPIError,
            update_external_card,
            self.payment_profile.external_api_id,
            SAMPLE_PROFILE_RESPONSE['cards'][0]['id'],
            SINGLE_USE_TOKEN
        )
        self.assertRaises(
            PaymentAPIError,
            create_external_payment_profile,
            self.user
        )
        self.assertRaises(
            PaymentAPIError,
            get_external_payment_profile,
            self.payment_profile.external_api_id
        )

    @responses.activate
    def test_known_external_api_exception(self):
        """
        Ensure we catch and handle some errors of the external API.
        """
        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )
        responses.add(
            responses.PUT,
            "http://example.com/customervault/v1/profiles/123/cards/456",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )
        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )
        responses.add(
            responses.GET,
            "http://example.com/customervault/v1/profiles/123?fields=cards",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )
        self.assertRaises(
            PaymentAPIError,
            charge_payment,
            1000,
            PAYMENT_TOKEN,
            "123"
        )
        self.assertRaises(
            PaymentAPIError,
            create_external_card,
            self.payment_profile.external_api_id,
            SINGLE_USE_TOKEN
        )
        self.assertRaises(
            PaymentAPIError,
            update_external_card,
            self.payment_profile.external_api_id,
            SAMPLE_PROFILE_RESPONSE['cards'][0]['id'],
            SINGLE_USE_TOKEN
        )
        self.assertRaises(
            PaymentAPIError,
            create_external_payment_profile,
            self.user
        )
        self.assertRaises(
            PaymentAPIError,
            get_external_payment_profile,
            self.payment_profile.external_api_id
        )

    def test_validate_coupon_for_order_with_most_exp_product(self):

        self.user.faculty = "Random faculty"
        self.user.student_number = "Random code"
        self.user.academic_program_code = "Random code"
        self.user.save()

        order_line_most_exp_product = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package_most_exp_product.id,
            cost=self.package_most_exp_product.price,
        )
        order_line_les_exp_product = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package_less_exp_product.id,
            cost=self.package_less_exp_product.price,
        )

        coupon_info = validate_coupon_for_order(self.coupon, self.order)

        error = coupon_info.get('error')

        self.assertIsNone(error)

        coupon_info_order_line = coupon_info.get('orderline')
        self.assertIsNotNone(coupon_info_order_line)
        self.assertEqual(coupon_info_order_line.id,
                         order_line_most_exp_product.id)
