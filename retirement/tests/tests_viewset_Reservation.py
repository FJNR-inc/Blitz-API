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

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.admin = AdminFactory()
        self.retirement_type = ContentType.objects.get_for_model(Retirement)
        self.retirement = Retirement.objects.create(
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
        self.retirement2 = Retirement.objects.create(
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
        self.retirement_overlap = Retirement.objects.create(
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
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.retirement_type,
            object_id=self.retirement.id,
            cost=self.retirement.price,
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            retirement=self.retirement,
            order_line=self.order_line,
            is_active=True,
        )
        self.reservation_expected_payload = {
            'id': self.reservation.id,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/' +
                          str(self.reservation.retirement.id),
            'url': 'http://testserver/retirement/reservations/' +
                   str(self.reservation.id),
            'user': 'http://testserver/users/' + str(self.user.id),
            'order_line': 'http://testserver/order_lines/' +
                          str(self.order_line.id),
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None,
            'refundable': True,
            'exchangeable': True,
        }
        self.reservation_admin = Reservation.objects.create(
            user=self.admin,
            retirement=self.retirement2,
            order_line=self.order_line,
            is_active=True,
        )

        self.maxDiff = None

    def test_create(self):
        """
        Ensure we can create a reservation if user has permission.
        It is possible to create reservations for INACTIVE retirements.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement2.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=response.content.decode("utf-8")
        )

        response_data = json.loads(response.content)
        response_data['retirement_details'] = remove_translation_fields(
            response_data['retirement_details']
        )
        response_data['user_details'] = remove_translation_fields(
            response_data['user_details']
        )
        del response_data['user_details']["first_name"]
        del response_data['user_details']["last_name"]
        del response_data['user_details']["email"]
        del response_data['user_details']['date_joined']
        del response_data['retirement_details']['reservations']
        del response_data['id']
        del response_data['url']

        content = {
            'is_active': True,
            'is_present': False,
            'user': 'http://testserver/users/' + str(self.user.id),
            'cancelation_action': None,
            'cancelation_date': None,
            'cancelation_reason': None,
            'refundable': False,
            'exchangeable': False,
            'retirement': 'http://testserver/retirement/retirements/' +
                          str(self.retirement2.id),
            'order_line': None,
            'retirement_details': {
                'activity_language': None,
                'end_time': '2130-02-17T12:00:00-05:00',
                'id': self.retirement2.id,
                'exclusive_memberships': [],
                'places_remaining': 38,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '199.00',
                'start_time': '2130-02-15T08:00:00-05:00',
                'users': [
                    'http://testserver/users/' + str(self.admin.id),
                    'http://testserver/users/' + str(self.user.id)
                ],
                'address_line1': '123 random street',
                'address_line2': None,
                'city': '',
                'country': 'Random country',
                'details': 'This is a description of the retirement.',
                'email_content': None,
                'latitude': None,
                'longitude': None,
                'name': 'random_retirement',
                'pictures': [],
                'postal_code': '123 456',
                'reserved_seats': 0,
                'seats': 40,
                'state_province': 'Random state',
                'timezone': None,
                'reservations_canceled': [],
                'total_reservations': 2,
                'refund_rate': 100,
                'min_day_refund': 7,
                'min_day_exchange': 7,
                'is_active': False,
                'accessibility': True,
                'form_url': 'example.com',
                'carpool_url': 'example2.com',
                'review_url': 'example3.com',
                'place_name': '',
                'url': 'http://testserver/retirement/retirements/' +
                       str(self.retirement2.id),
                'has_shared_rooms': True,
            },
            'user_details': {
                'academic_field': None,
                'academic_level': None,
                'birthdate': None,
                'gender': None,
                'groups': [],
                'id': self.user.id,
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'last_login': None,
                'membership': None,
                'membership_end': None,
                'other_phone': None,
                'phone': None,
                'tickets': 1,
                'university': None,
                'url': 'http://testserver/users/' + str(self.user.id),
                'user_permissions': [],
                'city': None,
                'personnal_restrictions': None,
                'academic_program_code': None,
                'faculty': None,
                'student_number': None,
                'volunteer_for_workplace': [],
            }
        }

        self.assertCountEqual(response_data['retirement_details']['users'],
                              content['retirement_details']['users'])

        del response_data['retirement_details']['users']
        del content['retirement_details']['users']

        self.assertEqual(response_data, content)

    def test_create_without_permission(self):
        """
        Ensure we can't create a reservation if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_overlapping(self):
        """
        Ensure we can't create reservations with overlapping retirement for the
        same user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse(
                'retirement:retirement-detail',
                args=[self.retirement_overlap.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
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
        Ensure we can't create a reservation with a non-existent retirement or
        user.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'retirement': reverse('retirement:retirement-detail', args=[999]),
            'user': reverse('user-detail', args=[999]),
            'order_line': reverse('orderline-detail', args=[999]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'retirement': ['Invalid hyperlink - Object does not exist.'],
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
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field is required.'],
            'retirement': ['This field is required.'],
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
            'retirement': None,
            'order_line': None,
            'is_active': None,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['This field may not be null.'],
            'retirement': ['This field may not be null.'],
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
            'retirement': "invalid",
            'order_line': "invalid",
            'is_active': "invalid",
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'user': ['Invalid hyperlink - No URL match.'],
            'retirement': ['Invalid hyperlink - No URL match.'],
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

        self.retirement2.seats = 0
        self.retirement2.save()

        data = {
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement2.id]
            ),
            'user': reverse('user-detail', args=[self.user.id]),
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "This retirement doesn't have available places. Please "
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
            reverse('retirement:reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        del data['results'][0]['user_details']
        del data['results'][0]['retirement_details']
        del data['results'][1]['user_details']
        del data['results'][1]['retirement_details']

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [
                self.reservation_expected_payload,
                {
                    'id': self.reservation_admin.id,
                    'is_active': True,
                    'is_present': False,
                    'retirement': 'http://testserver/retirement/retirements/' +
                                  str(self.retirement2.id),
                    'url': 'http://testserver/retirement/reservations/' +
                           str(self.reservation_admin.id),
                    'user': 'http://testserver/users/' + str(self.admin.id),
                    'order_line': 'http://testserver/order_lines/' +
                                  str(self.order_line.id),
                    'cancelation_date': None,
                    'cancelation_action': None,
                    'cancelation_reason': None,
                    'refundable': True,
                    'exchangeable': True,
                }
            ]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_as_non_admin(self):
        """
        Ensure that a user can list its reservations.
        Be wary: a user can see the list of user ID that are associated with
                 the reservation's retirement.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('retirement:reservation-list'),
            format='json',
        )

        data = json.loads(response.content)

        del data['results'][0]['user_details']
        del data['results'][0]['retirement_details']

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [self.reservation_expected_payload]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure that a user can read one of his reservations.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation.id},
            ),
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        self.assertEqual(response_data, self.reservation_expected_payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a reservation as non_admin if it is not owned.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retirement:reservation-detail',
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
                'retirement:retirement-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @responses.activate
    def test_delete(self):
        """
        Ensure that a user can cancel one of his retirement reservations.
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
                    'retirement:reservation-detail',
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
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_action, 'R')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 1)

    def test_delete_late(self):
        """
        Ensure that a user can cancel one of his retirement reservations.
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
                    'retirement:reservation-detail',
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
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_action, 'N')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

    def test_delete_non_refundable(self):
        """
        Ensure that a user can cancel one of his retirement reservations.
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
                    'retirement:reservation-detail',
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
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_action, 'N')
        self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None

        self.assertEqual(len(mail.outbox), 0)

        self.reservation.refundable = True
        self.reservation.save()

    @responses.activate
    def test_delete_scheduler_error(self):
        """
        Ensure emails were sent to admins if the API fails to schedule
        notifications.
        """
        self.client.force_authenticate(user=self.admin)

        self.retirement2.seats = self.retirement2.total_reservations
        self.retirement2.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/"
            "settlements/1/refunds",
            json=SAMPLE_REFUND_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            settings.EXTERNAL_SCHEDULER['URL'],
            status=400
        )

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retirement:reservation-detail',
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
        self.assertEqual(self.reservation_admin.cancelation_reason, 'U')
        self.assertEqual(self.reservation_admin.cancelation_action, 'R')
        self.assertEqual(self.reservation_admin.cancelation_date, FIXED_TIME)

        self.reservation_admin.is_active = True
        self.reservation_admin.cancelation_date = None
        self.reservation_admin.cancelation_reason = None

        # 1 mail for the refund
        # X mails to every admin
        self.assertGreater(len(mail.outbox), 1, "Invalid sent mail count")

        self.retirement2.seats = 400
        self.retirement2.save()

    def test_delete_not_owner(self):
        """
        Ensure that a user can't delete a reservation that he doesn't own.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': self.reservation_admin.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
                'retirement:reservation-detail',
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
                'retirement:reservation-detail',
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
        self.assertEqual(self.reservation.cancelation_reason, 'U')
        self.assertEqual(self.reservation.cancelation_action, 'R')

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
                    'retirement:reservation-detail',
                    kwargs={'pk': self.reservation.id},
                ),
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        content = {
            'non_field_errors': "The order has not been charged yet. Try "
                                "again later."
        }

        self.assertEqual(json.loads(response.content), content)

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
        Ensure that a user can cancel one of his retirement reservations.
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
                    'retirement:reservation-detail',
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
