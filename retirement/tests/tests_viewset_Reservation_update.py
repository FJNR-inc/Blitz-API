import json
import pytz
import responses

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core import mail
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from unittest import mock

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.services import remove_translation_fields

from store.models import Order, OrderLine, Refund
from store.tests.paysafe_sample_responses import (SAMPLE_REFUND_RESPONSE,
                                                  SAMPLE_NO_AMOUNT_TO_REFUND,
                                                  SAMPLE_PAYMENT_RESPONSE,
                                                  SAMPLE_PROFILE_RESPONSE,
                                                  SAMPLE_CARD_RESPONSE,
                                                  UNKNOWN_EXCEPTION, )

from ..models import Retirement, Reservation

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)
TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


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
class ReservationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.retirement_type = ContentType.objects.get_for_model(Retirement)
        cls.retirement = Retirement.objects.create(
            name="mega_retirement",
            details="This is a description of the mega retirement.",
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
            reserved_seats=1,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
        )
        cls.retirement2 = Retirement.objects.create(
            name="random_retirement",
            details="This is a description of the retirement.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            is_active=False,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
        )
        cls.retirement_overlap = Retirement.objects.create(
            name="ultra_retirement",
            details="This is a description of the ultra retirement.",
            seats=400,
            address_line1="1234 random street",
            postal_code="654 321",
            state_province="Random state 2",
            country="Random country 2",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.retirement_type,
            object_id=cls.retirement.id,
            cost=cls.retirement.price,
        )
        cls.reservation = Reservation.objects.create(
            user=cls.user,
            retirement=cls.retirement,
            order_line=cls.order_line,
            is_active=True,
        )
        cls.reservation_expected_payload = {
            'id': cls.reservation.id,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/' +
                          str(cls.reservation.retirement.id),
            'url': 'http://testserver/retirement/reservations/' +
                   str(cls.reservation.id),
            'user': 'http://testserver/users/' +
                    str(cls.user.id),
            'order_line': 'http://testserver/order_lines/' +
                          str(cls.order_line.id),
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None,
            'refundable': True,
            'exchangeable': True,
        }
        cls.reservation_non_exchangeable = Reservation.objects.create(
            user=cls.admin,
            retirement=cls.retirement,
            order_line=cls.order_line,
            is_active=True,
            exchangeable=False,
        )

    def test_update(self):
        """
        Ensure we can't update a reservation.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': False,
        }

        response = self.client.put(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def test_update_partial(self):
        """
        Ensure we can partially update a reservation (is_present field and
        retirement field only).
        The retirement can be changed if we're at least 'min_day_exchange' days
        before the event and if the new retirement is cheaper/same price.
        Otherwise, only 'is_present' can be updated.
        Sends an email to the user with the new retirement's info.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = self.reservation_expected_payload.copy()
        content['is_present'] = True
        content['retirement'] = 'http://testserver' + reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            )

        self.assertEqual(response_data, content)

        canceled_reservation = Reservation.objects.filter(is_active=False)[0]

        self.assertTrue(canceled_reservation)
        self.assertEqual(canceled_reservation.cancelation_action, 'E')
        self.assertEqual(canceled_reservation.cancelation_reason, 'U')
        self.assertEqual(canceled_reservation.cancelation_date, FIXED_TIME)
        self.assertEqual(canceled_reservation.retirement, self.retirement)
        self.assertEqual(canceled_reservation.order_line, self.order_line)

        # 1 email confirming the exchange
        # 1 email confirming participation to the new retirement
        self.assertEqual(len(mail.outbox), 2)

    def test_update_partial_is_present(self):
        """
        Ensure we can partially update a reservation (is_present).
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = self.reservation_expected_payload.copy()
        content['is_present'] = True

        self.assertEqual(response_data, content)

        self.assertEqual(len(mail.outbox), 0)

    def test_update_partial_ordered_more_than_1(self):
        """
        Ensure we can't update a reservation if it has more implication than
        predicted. (order.quantity > 1)
        """
        self.client.force_authenticate(user=self.admin)

        self.order_line.quantity = 2
        self.order_line.save()

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "The order containing this reservation has a quantity "
                "bigger than 1. Please contact the support team."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_no_place_left(self):
        """
        Ensure we can't update a reservation if the new retirement has no free
        place left.
        """
        self.client.force_authenticate(user=self.admin)

        self.retirement2.seats = 0
        self.retirement2.save()

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested retirement."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_same_retirement(self):
        """
        Ensure we can't update a reservation if the new retirement has no free
        place left.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'retirement': [
                "That retirement is already assigned to this object."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_without_proper_fields(self):
        """
        Ensure we can't partially update a reservation (other fields).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_active': False,
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Only is_present and retirement can be updated. To change "
                "other fields, delete this reservation and create a new one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_not_in_min_day_exchange(self):
        """
        Ensure we can't change retirement if not respecting min_day_refund.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2130, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Maximum exchange date exceeded."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_overlapping(self):
        """
        Ensure we can't change retirement if it overlaps with another
        reservation.
        """
        self.client.force_authenticate(user=self.admin)

        reservation_user = Reservation.objects.create(
            user=self.user,
            retirement=self.retirement2,
            order_line=self.order_line,
            is_active=True,
        )

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement_overlap.id},
            ),
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': reservation_user.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "This reservation overlaps with another active "
                "reservations for this user."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_more_expensive_retirement_missing_info(self):
        """
        Ensure we can't change retirement if the new one is more expensive and
        no payment_token or single_use_token is provided.
        """
        self.client.force_authenticate(user=self.admin)

        self.retirement2.price = 999
        self.retirement2.save()

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "The new retirement is more expensive than the current one. "
                "Provide a payment_token or single_use_token to charge the "
                "balance."
            ]
        }

        self.assertEqual(response_data, content)

        self.retirement2.price = 199
        self.retirement2.save()

    @responses.activate
    def test_update_partial_more_expensive_retirement(self):
        """
        Ensure we can change retirement if the new one is more expensive and
        a payment_token or single_use_token is provided.
        """
        self.client.force_authenticate(user=self.user)

        self.retirement2.price = 999
        self.retirement2.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
            'payment_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        # Validate the new order
        new_order = Order.objects.filter(transaction_date=FIXED_TIME)[0]

        self.assertTrue(new_order)
        self.assertEqual(new_order.transaction_date, FIXED_TIME)
        self.assertEqual(new_order.user, self.user)

        # Validate the new orderline
        self.reservation.refresh_from_db()
        new_orderline = self.reservation.order_line

        self.assertFalse(self.order_line == new_orderline)
        self.assertEqual(new_orderline.order, new_order)
        self.assertEqual(new_orderline.object_id, self.retirement2.id)
        self.assertEqual(new_orderline.content_type.model, "retirement")
        self.assertEqual(new_orderline.quantity, 1)

        # Validate the response
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = self.reservation_expected_payload.copy()
        content['retirement'] = 'http://testserver' + reverse(
            'retirement:retirement-detail',
            kwargs={'pk': self.retirement2.id},
        )
        content['order_line'] = 'http://testserver/order_lines/' + \
                                str(new_orderline.id)

        self.assertEqual(response_data, content)

        # Validate the canceled reservation
        canceled_reservation = Reservation.objects.filter(is_active=False)[0]

        self.assertTrue(canceled_reservation)
        self.assertEqual(canceled_reservation.cancelation_action, 'E')
        self.assertEqual(canceled_reservation.cancelation_reason, 'U')
        self.assertEqual(canceled_reservation.cancelation_date, FIXED_TIME)
        self.assertEqual(canceled_reservation.retirement, self.retirement)
        self.assertEqual(canceled_reservation.order_line, self.order_line)

        # Validate the full refund on old orderline
        refund = Refund.objects.filter(orderline=self.order_line)[0]

        self.assertTrue(refund)

        refund_amount = self.retirement.price * (Decimal(TAX_RATE) + 1)

        self.assertEqual(
            refund.amount,
            refund_amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        )
        self.assertEqual(refund.refund_date, FIXED_TIME)

        # 1 mail confirming the exchange
        # 1 mail confirming the participation to the new retirement
        # 1 mail confirming the new order
        self.assertEqual(len(mail.outbox), 3)

        self.retirement2.price = 199
        self.retirement2.save()

    @responses.activate
    def test_update_partial_more_expensive_retirement_single_use_token(self):
        """
        Ensure we can change retirement if the new one is more expensive and
        a payment_token or single_use_token is provided.
        """
        self.client.force_authenticate(user=self.user)

        self.retirement2.price = 999
        self.retirement2.save()

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

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
            'single_use_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        # Validate the new order
        new_order = Order.objects.filter(transaction_date=FIXED_TIME)[0]

        self.assertTrue(new_order)
        self.assertEqual(new_order.transaction_date, FIXED_TIME)
        self.assertEqual(new_order.user, self.user)

        # Validate the new orderline
        self.reservation.refresh_from_db()
        new_orderline = self.reservation.order_line

        self.assertFalse(self.order_line == new_orderline)
        self.assertEqual(new_orderline.order, new_order)
        self.assertEqual(new_orderline.object_id, self.retirement2.id)
        self.assertEqual(new_orderline.content_type.model, "retirement")
        self.assertEqual(new_orderline.quantity, 1)

        # Validate response
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = self.reservation_expected_payload.copy()
        content['retirement'] = 'http://testserver' + reverse(
            'retirement:retirement-detail',
            kwargs={'pk': self.retirement2.id},
        )
        content['order_line'] = 'http://testserver/order_lines/' + \
                                str(new_orderline.id)

        # Validate the canceled reservation
        canceled_reservation = Reservation.objects.filter(is_active=False)[0]

        self.assertTrue(canceled_reservation)
        self.assertEqual(canceled_reservation.cancelation_action, 'E')
        self.assertEqual(canceled_reservation.cancelation_reason, 'U')
        self.assertEqual(canceled_reservation.cancelation_date, FIXED_TIME)
        self.assertEqual(canceled_reservation.retirement, self.retirement)
        self.assertEqual(canceled_reservation.order_line, self.order_line)

        # Validate the full refund on old orderline
        refund = Refund.objects.filter(orderline=self.order_line)[0]

        self.assertTrue(refund)

        refund_amount = self.retirement.price * (Decimal(TAX_RATE) + 1)

        self.assertEqual(
            refund.amount,
            refund_amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        )
        self.assertEqual(refund.refund_date, FIXED_TIME)

        # 1 mail confirming the exchange
        # 1 mail confirming the participation to the new retirement
        # 1 mail confirming the new order
        self.assertEqual(len(mail.outbox), 3)

        self.retirement2.price = 199
        self.retirement2.save()

    @responses.activate
    def test_update_partial_less_expensive_retirement(self):
        """
        Ensure we can change retirement if the new one is less expensive. A
        refund will be issued.
        """
        self.client.force_authenticate(user=self.user)

        self.retirement2.price = 99
        self.retirement2.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = self.reservation_expected_payload.copy()
        content['retirement'] = 'http://testserver' + reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            )

        self.assertEqual(response_data, content)

        # Validate that a canceled reservation is created
        canceled_reservation = Reservation.objects.filter(is_active=False)[0]

        self.assertTrue(canceled_reservation)
        self.assertEqual(canceled_reservation.cancelation_action, 'E')
        self.assertEqual(canceled_reservation.cancelation_reason, 'U')
        self.assertEqual(canceled_reservation.cancelation_date, FIXED_TIME)
        self.assertEqual(canceled_reservation.retirement, self.retirement)
        self.assertEqual(canceled_reservation.order_line, self.order_line)

        # Validate that the refund object has been created
        refund = Refund.objects.filter(
            orderline=self.reservation.order_line
        )[0]

        self.assertTrue(refund)
        tax_rate = Decimal(TAX_RATE + 1)
        amount = (self.retirement.price - self.retirement2.price) * tax_rate
        self.assertEqual(
            refund.amount,
            amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        )
        self.assertEqual(refund.refund_date, FIXED_TIME)

        # 1 mail confirming the exchange
        # 1 mail confirming the participation to the new retirement
        # 1 mail confirming the refund
        self.assertEqual(len(mail.outbox), 3)

        self.retirement2.price = 199
        self.retirement2.save()

    def test_update_partial_with_forbidden_fields(self):
        """
        Ensure we can't partially update a reservation (other fields).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'is_active': False,
            'is_present': True,
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Only is_present and retirement can be updated. To change "
                "other fields, delete this reservation and create a new one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_non_exchangeable(self):
        """
        Ensure we can't change a reservation's retirement if the reservation
        is marked as non-exchangeable.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                kwargs={'pk': self.retirement2.id},
            ),
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation_non_exchangeable.pk},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "This reservation is not exchangeable. Please contact us "
                "to make any changes to this reservation."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
