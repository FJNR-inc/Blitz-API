import json

from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIRequestFactory

from blitz_api.factories import UserFactory, RetreatFactory, AdminFactory
from blitz_api.services import remove_translation_fields
from retirement.models import Retreat
from store.models import Order, OptionProduct


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
    def setUp(self):
        self.user = UserFactory()
        self.admin = AdminFactory()
        self.retreat = RetreatFactory()
        self.retreat.is_active = True
        self.retreat.save()
        self.retreat_content_types = ContentType.objects.get_for_model(Retreat)
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        factory = APIRequestFactory()
        self.request = factory.get('/')

        self.options_1: OptionProduct = OptionProduct.objects.create(
            name="options_1",
            details="options_1",
            available=True,
            price=50.00,
            max_quantity=10,
        )
        self.options_1.available_on_products.add(self.retreat)

    def test_create(self):

        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "basic_option",
            'details': "Basic option",
            'available': True,
            'price': '50.00',
            'max_quantity': 10,
        }

        response = self.client.post(
            reverse('optionproduct-list'),
            data,
            format='json',
        )

        response_content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)

        for key, value in data.items():
            self.assertEqual(
                response_content.get(key),
                value
            )

        self.assertIsNotNone(
            OptionProduct.objects.get(id=response_content.get('id'))
        )

    def test_create_with_product_type(self):

        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "basic_option",
            'details': "Basic option",
            'available': True,
            'price': '50.00',
            'max_quantity': 10,
            'available_on_product_types':
                [self.retreat_content_types.model]
        }

        response = self.client.post(
            reverse('optionproduct-list'),
            data,
            format='json',
        )

        response_content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)

        for key, value in data.items():
            self.assertEqual(
                response_content.get(key),
                value,
                f'Field tested: {key}'
            )

        self.assertIsNotNone(
            OptionProduct.objects.get(id=response_content.get('id'))
        )

        self.retreat.refresh_from_db()
        options_0 = self.retreat.options[0]

        self.assertIn(options_0,
                      list(self.retreat.options),
                      response_content.get('id'))

    def test_create_with_product(self):

        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "basic_option",
            'details': "Basic option",
            'available': True,
            'price': '50.00',
            'max_quantity': 10,
            'available_on_products':
                [self.retreat.id]
        }

        response = self.client.post(
            reverse('optionproduct-list'),
            data,
            format='json',
        )

        response_content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)

        for key, value in data.items():
            self.assertEqual(
                response_content.get(key),
                value,
                f'Field tested: {key}'
            )

        self.assertIsNotNone(
            OptionProduct.objects.get(id=response_content.get('id'))
        )

        self.retreat.refresh_from_db()
        options_0 = self.retreat.options[0]

        self.assertIn(options_0,
                      list(self.retreat.options),
                      response_content.get('id'))

    def test_get_option_on_retreat(self):

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        )

        response_content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK,
                         response.content)

        self.assertEqual(response_content.get('options')[0].get('id'),
                         self.options_1.id,
                         response_content)

        self.assertEqual(
            response_content.get('options')[0].get('max_quantity'),
            self.options_1.max_quantity,
            response_content)

    def test_delete_as_admin(self):

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'optionproduct-detail',
                args=[self.options_1.id]
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )

        self.options_1.refresh_from_db()

        self.assertFalse(self.options_1.available)
