import json
import pytz

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.utils import timezone
from datetime import datetime
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import (
    APITestCase,
    APIRequestFactory,
)

from blitz_api.factories import (
    UserFactory,
    AdminFactory,
)
from retirement.models import (
    Retreat,
    RetreatType,
    RetreatDate,
)
from store.models import (
    Order,
    OptionProduct,
)

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
    def setUp(self):
        self.user = UserFactory()
        self.admin = AdminFactory()
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
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
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8),
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()

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
