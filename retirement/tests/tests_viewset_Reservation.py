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
        cls.reservation_admin = Reservation.objects.create(
            user=cls.admin,
            retirement=cls.retirement2,
            order_line=cls.order_line,
            is_active=True,
        )

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
            'order_line': reverse(
                'orderline-detail', args=[self.order_line.id]),
            'is_active': True,
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

        content = {
            'id': 3,
            'is_active': True,
            'is_present': False,
            'url': 'http://testserver/retirement/reservations/3',
            'user': 'http://testserver/users/1',
            'cancelation_action': None,
            'cancelation_date': None,
            'cancelation_reason': None,
            'retirement': 'http://testserver/retirement/retirements/2',
            'order_line': 'http://testserver/order_lines/1',
            'retirement_details': {
                'activity_language': None,
                'end_time': '2130-02-17T12:00:00-05:00',
                'id': 2,
                'exclusive_memberships': [],
                'places_remaining': 38,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '199.00',
                'start_time': '2130-02-15T08:00:00-05:00',
                'url': 'http://testserver/retirement/retirements/1',
                'users': [
                    'http://testserver/users/2',
                    'http://testserver/users/1'
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
                'reservations': [
                    'http://testserver/retirement/reservations/2',
                    'http://testserver/retirement/reservations/3'
                ],
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
                'url': 'http://testserver/retirement/retirements/2'
            },
            'user_details': {
                'academic_field': None,
                'academic_level': None,
                'birthdate': None,
                'gender': None,
                'groups': [],
                'id': 1,
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
                'url': 'http://testserver/users/1',
                'user_permissions': [],
                'city': None,
                'personnal_restrictions': None,
                'academic_program_code': None,
                'faculty': None,
                'student_number': None,
            }
        }

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
        Ensure we can create the same reservation multiple times. This does
        not duplicate the entry and instead returns the existing one.
        """
        self.client.force_authenticate(user=self.admin)

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

        content = {
            'id': 3,
            'is_active': True,
            'is_present': False,
            'url': 'http://testserver/retirement/reservations/3',
            'user': 'http://testserver/users/1',
            'cancelation_action': None,
            'cancelation_date': None,
            'cancelation_reason': None,
            'retirement': 'http://testserver/retirement/retirements/2',
            'order_line': 'http://testserver/order_lines/1',
            'retirement_details': {
                'activity_language': None,
                'end_time': '2130-02-17T12:00:00-05:00',
                'id': 2,
                'exclusive_memberships': [],
                'places_remaining': 38,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '199.00',
                'start_time': '2130-02-15T08:00:00-05:00',
                'url': 'http://testserver/retirement/retirements/1',
                'users': [
                    'http://testserver/users/2',
                    'http://testserver/users/1'
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
                'reservations': [
                    'http://testserver/retirement/reservations/2',
                    'http://testserver/retirement/reservations/3'
                ],
                'reservations_canceled': [],
                'total_reservations': 2,
                'refund_rate': 100,
                'min_day_refund': 7,
                'min_day_exchange': 7,
                'is_active': False,
                'accessibility': True,
                'form_url': "example.com",
                'carpool_url': 'example2.com',
                'review_url': 'example3.com',
                'place_name': '',
                'url': 'http://testserver/retirement/retirements/2'
            },
            'user_details': {
                'academic_field': None,
                'academic_level': None,
                'birthdate': None,
                'gender': None,
                'groups': [],
                'id': 1,
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
                'url': 'http://testserver/users/1',
                'user_permissions': [],
                'city': None,
                'personnal_restrictions': None,
                'academic_program_code': None,
                'faculty': None,
                'student_number': None,
            }
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

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
            'order_line': ['This field is required.'],
            'is_active': ['This field is required.']
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
            'order_line': ['This field may not be null.'],
            'is_active': ['This field may not be null.']
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
            'is_active': ['"invalid" is not a valid boolean.'],
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
                kwargs={'pk': 2},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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

        content = {
            'id': 1,
            'is_active': True,
            'is_present': True,
            'retirement': 'http://testserver/retirement/retirements/2',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/1',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

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
                    kwargs={'pk': 1},
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

        content = {
            'id': 1,
            'is_active': True,
            'is_present': True,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/1',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

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
                kwargs={'pk': 2},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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
                kwargs={'pk': 2},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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
                kwargs={'pk': 1},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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
                kwargs={'pk': 1},
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
                kwargs={'pk': 2},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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
                kwargs={'pk': 3},
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
                kwargs={'pk': 2},
            ),
        }

        response = self.client.patch(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': 1},
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
                kwargs={'pk': 2},
            ),
            'payment_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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

        content = {
            'id': 1,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/2',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/2',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

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
                kwargs={'pk': 2},
            ),
            'single_use_token': "valid_token"
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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

        content = {
            'id': 1,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/2',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/2',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

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
                kwargs={'pk': 2},
            ),
        }

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.patch(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
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

        content = {
            'id': 1,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/2',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/1',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

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
                kwargs={'pk': 1},
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
            'results': [{
                'id': 1,
                'is_active': True,
                'is_present': False,
                'retirement': 'http://testserver/retirement/retirements/1',
                'url': 'http://testserver/retirement/reservations/1',
                'user': 'http://testserver/users/1',
                'order_line': 'http://testserver/order_lines/1',
                'cancelation_date': None,
                'cancelation_action': None,
                'cancelation_reason': None
            }, {
                'id': 2,
                'is_active': True,
                'is_present': False,
                'retirement': 'http://testserver/retirement/retirements/2',
                'url': 'http://testserver/retirement/reservations/2',
                'user': 'http://testserver/users/2',
                'order_line': 'http://testserver/order_lines/1',
                'cancelation_date': None,
                'cancelation_action': None,
                'cancelation_reason': None
            }]
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
            'results': [{
                'id': 1,
                'is_active': True,
                'is_present': False,
                'retirement': 'http://testserver/retirement/retirements/1',
                'url': 'http://testserver/retirement/reservations/1',
                'user': 'http://testserver/users/1',
                'order_line': 'http://testserver/order_lines/1',
                'cancelation_date': None,
                'cancelation_action': None,
                'cancelation_reason': None
            }]
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
                kwargs={'pk': 1},
            ),
        )

        response_data = json.loads(response.content)

        del response_data['user_details']
        del response_data['retirement_details']

        content = {
            'id': 1,
            'is_active': True,
            'is_present': False,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'order_line': 'http://testserver/order_lines/1',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a reservation as non_admin if it is not owned.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': 2},
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
                    kwargs={'pk': 1},
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
                    kwargs={'pk': 1},
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
                    kwargs={'pk': 2},
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
        self.assertTrue(len(mail.outbox) > 1, "Invalid sent mail count")

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

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        with mock.patch(
                'django.utils.timezone.now', return_value=FIXED_TIME):
            response = self.client.delete(
                reverse(
                    'retirement:reservation-detail',
                    kwargs={'pk': 1},
                ),
            )

        response = self.client.delete(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': 1},
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
                    kwargs={'pk': 1},
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
                    kwargs={'pk': 1},
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
