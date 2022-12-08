import json
import pytz
import responses

from datetime import datetime

from rest_framework import status
from rest_framework.test import APIClient

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core import mail
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from unittest import mock

from blitz_api.factories import (
    UserFactory,
    AdminFactory,
)
from blitz_api.testing_tools import CustomAPITestCase
from log_management.models import EmailLog

from store.models import (
    Order,
    OrderLine,
)
from store.tests.paysafe_sample_responses import (
    SAMPLE_REFUND_RESPONSE,
    SAMPLE_NO_AMOUNT_TO_REFUND,
    UNKNOWN_EXCEPTION,
)

from retirement.models import (
    Retreat,
    Reservation, RetreatType, RetreatDate,
)

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
class ReservationTests(CustomAPITestCase):
    ATTRIBUTES = [
        'id',
        'url',
        'inscription_date',
        'is_active',
        'is_present',
        'user',
        'cancelation_action',
        'cancelation_date',
        'cancelation_reason',
        'refundable',
        'exchangeable',
        'retreat',
        'order_line',
        'invitation',
        'post_event_send',
        'pre_event_send',
        'retreat_details',
        'user_details',
    ]

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.user2 = UserFactory()
        self.admin = AdminFactory()
        self.retreat_content_type = ContentType.objects.get_for_model(Retreat)
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
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
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
        self.retreat_overlap_conflict = Retreat.objects.create(
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
            retreat=self.retreat_overlap_conflict,
        )
        self.retreat_overlap_conflict.activate()

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
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 13, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 13, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 14, 12)),
            retreat=self.retreat_overlap,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 18, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 19, 12)),
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
            'user': 'http://testserver/users/' + str(self.user.id),
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
        self.reservation2 = Reservation.objects.create(
            user=self.user2,
            retreat=self.retreat,
            is_active=True,
        )
        self.reservation2_expected_payload = {
            'id': self.reservation2.id,
            'is_active': True,
            'is_present': False,
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.reservation2.retreat.id),
            'url': 'http://testserver/retreat/reservations/' +
                   str(self.reservation2.id),
            'user': 'http://testserver/users/' + str(self.user2.id),
            'order_line': None,
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None,
            'refundable': True,
            'exchangeable': True,
            'invitation': None,
            'post_event_send': False,
            'pre_event_send': False,
        }
        self.reservation_admin = Reservation.objects.create(
            user=self.admin,
            retreat=self.retreat2,
            order_line=self.order_line,
            is_active=True,
        )

    def test_create(self):
        """
        Ensure we can create a reservation if user has permission.
        It is possible to create reservations for INACTIVE retreats.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat2.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        content = json.loads(response.content)
        self.assertEqual(
            content['user_details']['url'],
            'http://testserver/users/' + str(self.user.id)
        )
        self.check_attributes(content)

    def test_create_without_permission(self):
        """
        Ensure we can't create a reservation if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_overlapping_without_conflict(self):
        """
        Ensure we can create reservations with overlapping retreat for the
        same user if the overlapping does not contain a conflict of date.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                args=[self.retreat_overlap.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        content = json.loads(response.content)

        self.assertEqual(
            content['user_details']['url'],
            'http://testserver/users/' + str(self.user.id)
        )
        self.check_attributes(content)

    def test_create_overlapping_with_conflict(self):
        """
        Ensure we can't create reservations with overlapping retreat for the
        same user if the overlapping contain a conflict of date.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail',
                args=[self.retreat_overlap_conflict.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'This reservation overlaps with another active reservations '
                'for this user.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_duplicate(self):
        """
        Ensure we cannot create the same reservation multiple times.
        Overlapping reservation error is sent
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'This reservation overlaps with another active reservations '
                'for this user.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_existent_period_user(self):
        """
        Ensure we can't create a reservation with a non-existent retreat or
        user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retreat': reverse('retreat:retreat-detail', args=[999]),
            'user': reverse('user-detail', args=[999]),
            'order_line': reverse('orderline-detail', args=[999]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'retreat': ['Invalid hyperlink - Object does not exist.'],
            'user': ['Invalid hyperlink - Object does not exist.'],
            'order_line': ['Invalid hyperlink - Object does not exist.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a reservation when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field is required.'],
            'retreat': ['This field is required.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_field(self):
        """
        Ensure we can't create a reservation when required field are blank.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': None,
            'retreat': None,
            'order_line': None,
            'is_active': None,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field may not be null.'],
            'retreat': ['This field may not be null.'],
            'is_active': ['This field may not be null.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a reservation when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': "invalid",
            'retreat': "invalid",
            'order_line': "invalid",
            'is_active': "invalid",
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['Invalid hyperlink - No URL match.'],
            'retreat': ['Invalid hyperlink - No URL match.'],
            'order_line': ['Invalid hyperlink - No URL match.'],
            'is_active': ['Must be a valid boolean.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_no_place_left(self):
        """
        Ensure we can't create a reservation if there is no place left
        """

        self.client.force_authenticate(user=self.admin)

        self.retreat2.seats = 0
        self.retreat2.save()

        data = {
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat2.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retreat:reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "This retreat doesn't have available places. Please "
                'check number of seats available and reserved seats.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list(self):
        """
        Ensure we can list reservations as an admin.
        """
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(content['count'], 3)

        self.check_attributes(content['results'][0])

    def test_list_as_non_admin(self):
        """
        Ensure that a user can list its reservations.
        Be wary: a user can see the list of user ID that are associated with
                 the reservation's retreat.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        del data['results'][0]['retreat_details']
        del data['results'][0]['inscription_date']

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [self.reservation_expected_payload]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_start_date(self):
        """
        Ensure that a user can filter its reservations by start_date
        """
        self.client.force_authenticate(user=self.user)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'start_after': '2200-01-01T00:00:00Z'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 0)

    def test_filter_by_end_date(self):
        """
        Ensure that a user can filter its reservations by end_date
        """
        self.client.force_authenticate(user=self.user)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'finish_after': '2200-01-01T00:00:00Z'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 0)

    def test_filter_by_is_active(self):
        """
        Ensure that a user can filter its reservations by is_active
        """
        self.client.force_authenticate(user=self.user)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'is_active': 'false'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 0)

    def test_filter_by_user(self):
        """
        Ensure that an admin can filter reservations by is_virtual
        """
        self.client.force_authenticate(user=self.admin)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 3)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'user': self.user.id
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

    def test_filter_by_retreat(self):
        """
        Ensure that an admin can filter reservations by retreat
        """
        self.client.force_authenticate(user=self.admin)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 3)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'retreat': self.retreat2.id
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

    def test_filter_by_is_virtual(self):
        """
        Ensure that a user can filter its reservations by is_virtual
        """
        self.client.force_authenticate(user=self.user)

        # First call without filter
        response = self.client.get(
            reverse('retreat:reservation-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 1)

        # Second call with a filter to comparate
        response = self.client.get(
            reverse('retreat:reservation-list'),
            {
                'retreat__type__is_virtual': 'true'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(content['count'], 0)

    def test_read(self):
        """
        Ensure that a user can read one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
        )

        response_data = json.loads(response.content)

        del response_data['retreat_details']
        del response_data['inscription_date']

        self.assertEqual(response_data, self.reservation_expected_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a reservation as non_admin if it is not owned.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation_admin.id},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a period that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'retreat:retreat-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @responses.activate
    def test_delete(self):
        """
        Ensure that a user can cancel one of his retreat reservations.
        By canceling 'min_day_refund' days or more before the event, the user
         will be refunded 'refund_rate'% of the price paid.
        The user will receive an email confirming the refund or inviting the
         user to contact the support if payment informations are no longer
         valid.
        If the user cancels less than 'min_day_refund' days before the event,
         no refund is made.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_REFUND
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 1)

    @responses.activate
    def test_delete_free(self):
        """
        Ensure that a user can cancel one of his retreat reservations
        that was free.
        The user will not have any refund since it was free, even
        by canceling 'min_day_refund' days or more before the
        event.
        The user won't receive any email.
        """
        order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.retreat_content_type,
            object_id=self.retreat.id,
            cost=0.0
        )

        free_reservation = Reservation.objects.create(
            user=self.user,
            retreat=self.retreat,
            order_line=order_line,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': free_reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        free_reservation.refresh_from_db()

        self.assertFalse(free_reservation.is_active)
        self.assertEqual(
            free_reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            free_reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(free_reservation.cancelation_date, FIXED_TIME)

        free_reservation.is_active = True
        free_reservation.cancelation_date = None
        free_reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @responses.activate
    def test_delete_late(self):
        """
        Ensure that a user can cancel one of his retreat reservations.
        This cancelation does not respect 'min_day_refund', thus the user
         will not be refunded.
        The user won't receive any email.
        """
        self.client.force_authenticate(user=self.user)

        FIXED_TIME = datetime(2130, 1, 10, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @responses.activate
    def test_delete_non_refundable(self):
        """
        Ensure that a user can cancel one of his retreat reservations.
        This cancelation does not respect 'refundable', thus the user
         will not be refunded.
        The user won't receive any email.
        """
        self.client.force_authenticate(user=self.user)

        self.reservation.refundable = False
        self.reservation.save()

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.pk},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

        self.reservation.refundable = True
        self.reservation.save()

    @responses.activate
    def test_delete_retirement_refundable_created_by_administrator(self):
        """
        Ensure that a user can cancel one of his retreat reservations
        created by an administrator.
        Since the user didn't bought this reservation via the platform
        via a manual administratior action he will not be automatically
        refund.
        The user won't receive any email.

        Test when refundable is True, but we will not refund
        """
        self.client.force_authenticate(user=self.user2)

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)

        self.assertTrue(self.reservation2.refundable)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation2.pk},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation2.refresh_from_db()

        self.assertFalse(self.reservation2.is_active)
        self.assertEqual(
            self.reservation2.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation2.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(self.reservation2.cancelation_date, FIXED_TIME)

        self.reservation2.is_active = True
        self.reservation2.cancelation_date = None
        self.reservation2.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @responses.activate
    def test_delete_retirement_not_refundable_created_by_administrator(self):
        """
        Ensure that a user can cancel one of his retreat reservations
        created by an administrator.
        Since the user didn't bought this reservation via the platform
        via a manual administratior action he will not be automatically
        refund.
        The user won't receive any email.

        Test when refundable is False, but we will not refund
        """
        self.client.force_authenticate(user=self.user2)

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)

        self.reservation2.refundable = False
        self.reservation2.save()

        self.reservation2.refresh_from_db()

        self.assertFalse(self.reservation2.refundable)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation2.pk},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation2.refresh_from_db()

        self.assertFalse(self.reservation2.is_active)
        self.assertEqual(
            self.reservation2.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation2.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(self.reservation2.cancelation_date, FIXED_TIME)

        self.reservation2.is_active = True
        self.reservation2.cancelation_date = None
        self.reservation2.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @responses.activate
    def test_delete_scheduler_working(self):
        """
        Ensure emails were sent to admins if the API fails to schedule
        notifications.
        """
        self.client.force_authenticate(user=self.admin)

        self.retreat2.seats = self.retreat2.total_reservations
        self.retreat2.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation_admin.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation_admin.refresh_from_db()

        self.assertFalse(self.reservation_admin.is_active)
        self.assertEqual(
            self.reservation_admin.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation_admin.cancelation_action,
            Reservation.CANCELATION_ACTION_REFUND
        )
        self.assertEqual(self.reservation_admin.cancelation_date,
                         FIXED_TIME)

        self.reservation_admin.is_active = True
        self.reservation_admin.cancelation_date = None
        self.reservation_admin.cancelation_reason = None

        self.retreat2.seats = 400
        self.retreat2.save()

    def test_delete_not_owner(self):
        """
        Ensure that a user can't delete a reservation that he doesn't own.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation_admin.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @responses.activate
    def test_delete_reservation_of_user_as_admin_no_refundable(self):
        """
        Ensure that an admin can cancel the reservations of a user.
        This cancelation does not respect 'refundable', the user
        will not be refunded.
        The user won't receive any email.
        """
        self.client.force_authenticate(user=self.admin)

        self.reservation.refundable = False
        self.reservation.save()

        FIXED_TIME = datetime(2000, 1, 10, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.pk},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_ADMIN_CANCELLED
        )
        self.assertEqual(
            self.reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_NONE
        )
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

        self.reservation.refundable = True
        self.reservation.save()

    def test_delete_orderline_quantity_too_big(self):
        """
        Ensure that a user can't delete a reservation if the orderline
        containing it has a quatity bigger than 1.
        """
        self.client.force_authenticate(user=self.admin)

        self.order_line.quantity = 2
        self.order_line.save()

        response = self.client.delete(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation_admin.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {
            'non_field_errors': [
                "The order containing this reservation has a quantity "
                "bigger than 1. Please contact the support team."
            ]
        }

        self.order_line.quantity = 1
        self.order_line.save()

    @responses.activate
    def test_delete_twice(self):
        """
        Ensure that a user can delete one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        response = self.client.delete(
            reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content
        )

        self.reservation.refresh_from_db()

        self.assertFalse(self.reservation.is_active)
        self.assertEqual(
            self.reservation.cancelation_reason,
            Reservation.CANCELATION_REASON_USER_CANCELLED
        )
        self.assertEqual(
            self.reservation.cancelation_action,
            Reservation.CANCELATION_ACTION_REFUND
        )

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 1)

    @responses.activate
    def test_delete_refund_too_fast(self):
        """
        Ensure that a user can't get a refund if the order payment has not been
        processed completely.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_NO_AMOUNT_TO_REFUND,
            status=400
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        content = {
            'non_field_errors': [
                "The order has not been charged yet. Try again later."
            ]
        }

        self.assertEqual(
            json.loads(response.content).get('non_field_errors'),
            content.get('non_field_errors'))

        self.reservation.refresh_from_db()

        self.assertTrue(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, None)
        self.assertEqual(self.reservation.cancelation_action, None)
        self.assertEqual(self.reservation.cancelation_date, None)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @responses.activate
    def test_delete_refund_error(self):
        """
        Ensure that a user can cancel one of his retreat reservations.
        By canceling 'min_day_refund' days or more before the event, the user
         will be refunded 'refund_rate'% of the price paid.
        The user will receive an email confirming the refund or inviting the
         user to contact the support if payment informations are no longer
         valid.
        If the user cancels less than 'min_day_refund' days before the event,
         no refund is made.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=UNKNOWN_EXCEPTION,
            status=400
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retreat:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        content = {
            'message': "The request could not be processed."
        }

        # Receiving a 'bytes' object, which is probably wrong...
        # self.assertEqual(json.dumps(response.content), content)

        self.reservation.refresh_from_db()

        self.assertTrue(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, None)
        self.assertEqual(self.reservation.cancelation_action, None)
        self.assertEqual(self.reservation.cancelation_date, None)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
        }
    )
    def test_remind_users(self):
        self.client.force_authenticate(user=self.admin)

        FIXED_TIME = datetime(2130, 1, 10, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.get(
                reverse(
                    'retreat:retreat-remind-users',
                    kwargs={'pk': self.retreat.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        MAIL_SERVICE = settings.ANYMAIL
        template = MAIL_SERVICE["TEMPLATES"].get('REMINDER_PHYSICAL_RETREAT')
        self.assertTrue(
            EmailLog.objects.filter(
                user_email=self.user.email,
                type_email='Template #' + str(template)
            )
        )

        self.assertEqual(
            EmailLog.objects.filter(
                user_email=self.user.email,
                type_email='Template #' + str(template)
            )[0].nb_email_sent,
            1
        )
