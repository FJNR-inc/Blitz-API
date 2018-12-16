import json
import pytz

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from unittest import mock

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.services import remove_translation_fields

from ..models import Retirement, Reservation

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class ReservationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(ReservationTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
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
        )
        cls.retirement2 = Retirement.objects.create(
            name="random_retirement",
            details="This is a description of the retirement.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 2, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            is_active=False,
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
        )
        cls.reservation = Reservation.objects.create(
            user=cls.user,
            retirement=cls.retirement,
            is_active=True,
        )
        cls.reservation_admin = Reservation.objects.create(
            user=cls.admin,
            retirement=cls.retirement2,
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
            'retirement_details': {
                'activity_language': None,
                'end_time': '2130-02-17T12:00:00-05:00',
                'id': 2,
                'exclusive_memberships': [],
                'places_remaining': 38,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '3.00',
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
                'personnal_restrictions': None
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
            'retirement_details': {
                'activity_language': None,
                'end_time': '2130-02-17T12:00:00-05:00',
                'id': 2,
                'exclusive_memberships': [],
                'places_remaining': 38,
                'next_user_notified': 0,
                'notification_interval': '1 00:00:00',
                'price': '3.00',
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
                'personnal_restrictions': None
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
            'is_active': True,
        }

        response = self.client.post(
            reverse('retirement:reservation-list'),
            data,
            format='json',
        )

        content = {
            'retirement': ['Invalid hyperlink - Object does not exist.'],
            'user': ['Invalid hyperlink - Object does not exist.']
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
        Ensure we can partially update a reservation (is_present field only).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
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

        del response_data['user_details']
        del response_data['retirement_details']

        content = {
            'id': 1,
            'is_active': True,
            'is_present': True,
            'retirement': 'http://testserver/retirement/retirements/1',
            'url': 'http://testserver/retirement/reservations/1',
            'user': 'http://testserver/users/1',
            'cancelation_date': None,
            'cancelation_action': None,
            'cancelation_reason': None
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial_without_is_pesent(self):
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
            'is_present': [
                "Only is_present can be updated. To change other "
                "fields, delete this reservation and create a new "
                "one."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

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
            'is_present': [
                "Only is_present can be updated. To change other "
                "fields, delete this reservation and create a new "
                "one."
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

    def test_delete(self):
        """
        Ensure that we can't delete a retirement.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retirement:reservation-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )
    # def test_delete(self):
    #     """
    #     Ensure that a user can delete one of his reservations.
    #     """
    #     self.client.force_authenticate(user=self.user)
    #
    #     FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)
    #
    #     with mock.patch(
    #             'workplace.views.timezone.now', return_value=FIXED_TIME):
    #         response = self.client.delete(
    #             reverse(
    #                 'retirement:reservation-detail',
    #                 kwargs={'pk': 1},
    #             ),
    #         )
    #
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #
    #     self.reservation.refresh_from_db()
    #
    #     self.assertFalse(self.reservation.is_active)
    #     self.assertEqual(self.reservation.cancelation_reason, 'U')
    #     self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)
    #
    #     self.reservation.is_active = True
    #     self.reservation.cancelation_date = None
    #     self.reservation.cancelation_reason = None
    #
    # def test_delete_as_admin(self):
    #     """
    #     Ensure that an admin can delete any reservations.
    #     """
    #     self.client.force_authenticate(user=self.admin)
    #
    #     FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)
    #
    #     with mock.patch(
    #             'workplace.views.timezone.now', return_value=FIXED_TIME):
    #         response = self.client.delete(
    #             reverse(
    #                 'retirement:reservation-detail',
    #                 kwargs={'pk': 1},
    #             ),
    #         )
    #
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #
    #     self.reservation.refresh_from_db()
    #
    #     self.assertFalse(self.reservation.is_active)
    #     self.assertEqual(self.reservation.cancelation_reason, 'U')
    #     self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)
    #
    #     self.reservation.is_active = True
    #     self.reservation.cancelation_date = None
    #     self.reservation.cancelation_reason = None
    #
    # def test_delete_not_owner(self):
    #     """
    #     Ensure that a user can't delete a reservation that he doesn't own.
    #     """
    #     self.client.force_authenticate(user=self.user)
    #
    #     response = self.client.delete(
    #         reverse(
    #             'retirement:reservation-detail',
    #             kwargs={'pk': self.reservation_admin.id},
    #         ),
    #     )
    #
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    #
    # def test_delete_twice(self):
    #     """
    #     Ensure that a user can delete one of his reservations.
    #     """
    #     self.client.force_authenticate(user=self.user)
    #
    #     FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)
    #
    #     with mock.patch(
    #             'workplace.views.timezone.now', return_value=FIXED_TIME):
    #         response = self.client.delete(
    #             reverse(
    #                 'retirement:reservation-detail',
    #                 kwargs={'pk': 1},
    #             ),
    #         )
    #
    #     response = self.client.delete(
    #         reverse(
    #             'retirement:reservation-detail',
    #             kwargs={'pk': 1},
    #         ),
    #     )
    #
    #     self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    #
    #     self.reservation.refresh_from_db()
    #
    #     self.assertFalse(self.reservation.is_active)
    #     self.assertEqual(self.reservation.cancelation_reason, 'U')
    #     self.assertEqual(self.reservation.cancelation_date, FIXED_TIME)
    #
    #     self.reservation.is_active = True
    #     self.reservation.cancelation_date = None
    #     self.reservation.cancelation_reason = None
