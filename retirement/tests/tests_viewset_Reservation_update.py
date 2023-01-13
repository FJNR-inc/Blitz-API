import json
import pytz
import responses

from datetime import datetime
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

from blitz_api.factories import UserFactory, AdminFactory, OptionProductFactory

from store.models import Order, OrderLine, Refund
from store.tests.paysafe_sample_responses import (
    SAMPLE_REFUND_RESPONSE,
    SAMPLE_PAYMENT_RESPONSE,
    SAMPLE_PROFILE_RESPONSE,
    SAMPLE_CARD_RESPONSE,
)

from ..models import Retreat, Reservation, RetreatType, RetreatDate

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

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.admin = AdminFactory()
        self.retreat_content_type = ContentType.objects.get_for_model(Retreat)
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
            template_id_for_welcome_message=1,
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
        self.retreat.add_wait_queue_place(self.user, generate_cron=False)

        self.retreat2 = Retreat.objects.create(
            name="random_retreat",
            details="This is a description of the retreat.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 2, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 17, 12)),
            retreat=self.retreat2,
        )

        self.retreat_overlap = Retreat.objects.create(
            name="ultra_retreat",
            details="This is a description of the ultra retreat.",
            seats=400,
            address_line1="1234 random street",
            postal_code="654 321",
            state_province="Random state 2",
            country="Random country 2",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat_overlap,
        )
        self.retreat_overlap.activate()

        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.retreat_content_type,
            object_id=self.retreat.id,
            cost=self.retreat.price,
            total_cost=self.retreat.price,
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            retreat=self.retreat,
            order_line=self.order_line,
            is_active=True,
        )
        self.reservation_expected_payload = {
            'id': self.reservation.id,
            'is_active': True,
            'is_present': False,
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.reservation.retreat.id),
            'url': 'http://testserver/retreat/reservations/' +
                   str(self.reservation.id),
            'user': 'http://testserver/users/' +
                    str(self.user.id),
            'order_line': 'http://testserver/order_lines/' +
                          str(self.order_line.id),
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None,
            'refundable': True,
            'exchangeable': True,
            'invitation': None,
            'post_event_send': False,
            'pre_event_send': False,
        }
        self.reservation_non_exchangeable = Reservation.objects.create(
            user=self.admin,
            retreat=self.retreat,
            order_line=self.order_line,
            is_active=True,
            exchangeable=False,
        )

    def test_update(self):
        """
        Ensure we can't update a reservation.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'is_active': False,
        }

        response = self.client.put(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                "POLICY_URL": "fake_url",
                "LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT": "fake_url",
                "PROFILE_URL": "fake_url"
            }
        }
    )
    def test_update_partial(self):
        """
        Ensure we can partially update a reservation (is_present field and
        retreat field only).
        The retreat can be changed if we're at least 'min_day_exchange' days
        before the event and if the new retreat is cheaper/same price.
        Otherwise, only 'is_present' can be updated.
        Sends an email to the user with the new retreat's info.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
        del response_data['retreat_details']
        del response_data['inscription_date']

        content = self.reservation_expected_payload.copy()
        content['is_present'] = True
        content['retreat'] = 'http://testserver' + reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            )

        self.assertEqual(response_data, content)

        canceled_reservation = Reservation.objects.filter(is_active=False)[0]

        self.assertTrue(canceled_reservation)
        self.assertEqual(
            canceled_reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_EXCHANGE
        )
        self.assertEqual(
            canceled_reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(canceled_reservation.cancelation_date, FIXED_TIME)
        self.assertEqual(canceled_reservation.retreat, self.retreat)
        self.assertEqual(canceled_reservation.order_line, self.order_line)

        # 1 email confirming the exchange
        # 1 email confirming participation to the new retreat
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
                    'retreat:reservation-detail',
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
        del response_data['retreat_details']
        del response_data['inscription_date']

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
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
        Ensure we can't update a reservation if the new retreat has no free
        place left.
        """
        self.client.force_authenticate(user=self.admin)

        self.retreat2.seats = 0
        self.retreat2.save()

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
                "There are no places left in the requested retreat."
            ]
        }

        self.assertEqual(response_data, content)

    def test_update_partial_same_retreat(self):
        """
        Ensure we can't update a reservation if the new retreat has no free
        place left.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2030, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'is_present': True,
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
            'retreat': [
                "That retreat is already assigned to this object."
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
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Only is_present and retreat can be updated. To change "
                "other fields, delete this reservation and create a new one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_not_in_min_day_exchange(self):
        """
        Ensure we can't change retreat if not respecting min_day_refund.
        """
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2130, 1, 10, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
        Ensure we can't change retreat if it overlaps with another
        reservation.
        """
        self.client.force_authenticate(user=self.admin)

        reservation_user = Reservation.objects.create(
            user=self.user,
            retreat=self.retreat2,
            order_line=self.order_line,
            is_active=True,
        )

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat_overlap.id},
            ),
        }

        response = self.client.patch(
            reverse(
                'retreat:reservation-detail',
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
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Only is_present and retreat can be updated. To change "
                "other fields, delete this reservation and create a new one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_non_exchangeable(self):
        """
        Ensure we can't change a reservation's retreat if the reservation
        is marked as non-exchangeable.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        response = self.client.patch(
            reverse(
                'retreat:reservation-detail',
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

    def test_cant_update_partial_less_expensive_retreat(self):
        """
        Ensure we can't change retreat if the new one is less expensive. A
        refund will be issued.
        """
        self.client.force_authenticate(user=self.user)

        self.retreat2.price = 99
        self.retreat2.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
                "You can only exchange for a retreat with the "
                "same price."
            ]
        }

        self.assertEqual(response_data, content)

    def test_cant_update_partial_more_expensive_retreat(self):
        """
        Ensure we can't change retreat if the new one is more expensive and
        a payment_token or single_use_token is provided.
        """
        self.client.force_authenticate(user=self.user)

        self.retreat2.price = 999
        self.retreat2.save()

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
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
            'payment_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
                "You can only exchange for a retreat with the "
                "same price."
            ]
        }

        self.assertEqual(response_data, content)

    def test_cant_update_partial_option_retreat(self):
        """
        Ensure we can't change retreat if the new one has options
        """
        self.client.force_authenticate(user=self.user)

        option = OptionProductFactory()
        option.available_on_products.add(self.retreat2)
        option.save()

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
            'retreat': reverse(
                'retreat:retreat-detail',
                kwargs={'pk': self.retreat2.id},
            ),
            'payment_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retreat:reservation-detail',
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
                "You can only exchange for a retreat without "
                "option."
            ]
        }

        self.assertEqual(response_data, content)
