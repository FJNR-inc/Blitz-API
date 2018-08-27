import json
import responses

from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from rest_framework import status
from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from .paysafe_sample_responses import (UNKNOWN_EXCEPTION,
                                       SAMPLE_INVALID_PAYMENT_TOKEN,
                                       SAMPLE_PROFILE_RESPONSE,)

from ..exceptions import PaymentAPIError
from ..models import PaymentProfile
from ..services import (charge_payment,
                        get_external_payment_profile,
                        create_external_payment_profile,
                        update_external_card,
                        create_external_card,)

User = get_user_model()

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

    @classmethod
    def setUpClass(cls):
        super(ServicesTests, cls).setUpClass()
        cls.user = UserFactory()
        cls.payment_profile = PaymentProfile.objects.create(
            name="Test profile",
            owner=cls.user,
            external_api_id="123",
            external_api_url="https://api.test.paysafe.com/customervault/v1/"
                             "profiles/",
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
