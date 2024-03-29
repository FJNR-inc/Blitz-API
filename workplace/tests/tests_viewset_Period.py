import json
import pytz

from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.core import mail
from django.contrib.auth import get_user_model
from django.test.utils import override_settings

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.services import remove_translation_fields

from ..models import Workplace, Period, TimeSlot, Reservation

User = get_user_model()
LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class PeriodTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PeriodTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.workplace = Workplace.objects.create(
            name="Blitz",
            seats=40,
            details="short_description",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.period = Period.objects.create(
            name="random_period",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=False,
        )
        cls.period_active = Period.objects.create(
            name="random_period_active",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.time_slot_active = TimeSlot.objects.create(
            period=cls.period_active,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 18)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 22)),
        )
        cls.reservation = Reservation.objects.create(
            user=cls.user,
            timeslot=cls.time_slot_active,
            is_active=True,
        )

    def test_create(self):
        """
        Ensure we can create a period if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': LOCAL_TIMEZONE.localize(
                datetime.now() +
                timedelta(weeks=5)),
            'end_date': LOCAL_TIMEZONE.localize(
                datetime.now() + timedelta(weeks=10)),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'end_date': data['end_date'].isoformat(),
            'is_active': True,
            'name': 'random_period',
            'price': '3.00',
            'total_reservations': 0,
            'start_date': data['start_date'].isoformat(),
            'workplace': f'http://testserver/workplaces/{self.workplace.id}'
        }

        response_content = json.loads(response.content)

        del response_content['id']
        del response_content['url']

        self.assertEqual(
            remove_translation_fields(response_content),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a period if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(weeks=4),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.post(
            reverse('period-list'),
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
        Ensure we can't create overlapping period in the same workplace.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(weeks=4),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'An active period associated to the same workplace overlaps '
                'with the provided start_date and end_date.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_start_end(self):
        """
        Ensure we can't create periods with start_date greater than end_date.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': timezone.now(),
            'end_date': timezone.now() - timedelta(weeks=4),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'end_date': ['End date must be later than start_date.'],
            'start_date': ['Start date must be earlier than end_date.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_existent_workplace(self):
        """
        Ensure we can't create a period with a non-existent workplace.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_period",
            'workplace': reverse('workplace-detail', args=[999]),
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(weeks=4),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {'workplace': ['Invalid hyperlink - Object does not exist.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a period when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'end_date': ['This field is required.'],
            'is_active': ['This field is required.'],
            'price': ['This field is required.'],
            'start_date': ['This field is required.'],
            'workplace': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_field(self):
        """
        Ensure we can't create a period when required field are blank.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': None,
            'workplace': None,
            'start_date': None,
            'end_date': None,
            'price': None,
            'is_active': None,
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'name': ['This field may not be null.'],
            'start_date': ['This field may not be null.'],
            'end_date': ['This field may not be null.'],
            'price': ['This field may not be null.'],
            'is_active': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a timeslot when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "",
            'workplace': "invalid",
            'start_date': "",
            'end_date': "",
            'price': "",
            'is_active': "",
        }

        response = self.client.post(
            reverse('period-list'),
            data,
            format='json',
        )

        content = {
            'end_date': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'is_active': ['Must be a valid boolean.'],
            'name': ['This field may not be blank.'],
            'price': ['A valid number is required.'],
            'start_date': [
                'Datetime has wrong format. Use one of these formats instead: '
                'YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'workplace': ['Invalid hyperlink - No URL match.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    """
    Full updates and partial updates are limited. If reservations exist, these
    actions are forbidden.
    In a future iteration, we could allow updates with the exception of:
        - Postpone start_date
        - Bring forward end_date
        - Set is_active to False
    """

    def test_update(self):
        """
        Ensure we can update a period without reservations.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "new_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': LOCAL_TIMEZONE.localize(
                datetime.now() + timedelta(weeks=5)),
            'end_date': LOCAL_TIMEZONE.localize(
                datetime.now() + timedelta(weeks=10)),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.put(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
            data,
            format='json',
        )

        content = {
            'id': self.period.id,
            'end_date': data['end_date'].isoformat(),
            'is_active': True,
            'name': 'new_period',
            'price': '3.00',
            'total_reservations': 0,
            'start_date': data['start_date'].isoformat(),
            'url': f'http://testserver/periods/{self.period.id}',
            'workplace': f'http://testserver/workplaces/{self.workplace.id}'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_with_reservations(self):
        """
        Ensure we can't update a period that contains time slots with
        reservations.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "new_period",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'start_date': timezone.now() + timedelta(weeks=5),
            'end_date': timezone.now() + timedelta(weeks=10),
            'price': '3.00',
            'is_active': True,
        }

        response = self.client.put(
            reverse(
                'period-detail',
                args=[self.period_active.id]
            ),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "The period contains timeslots with user reservations."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial(self):
        """
        Ensure we can partially update a period.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "updated_period",
            'start_date': LOCAL_TIMEZONE.localize(
                datetime.now() + timedelta(weeks=1)),
            'price': '2000.00',
        }

        response = self.client.patch(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'id': self.period.id,
            'is_active': False,
            'name': 'updated_period',
            'price': '2000.00',
            'total_reservations': 0,
            'end_date': response_data['end_date'],
            'start_date': data['start_date'].isoformat(),
            'url': f'http://testserver/periods/{self.period.id}',
            'workplace': f'http://testserver/workplaces/{self.workplace.id}'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial_with_reservations(self):
        """
        Ensure we can't partially update a period that contains time slots with
        reservations.
        The next step is to allow only these actions:
            - The start_date can be set to an earlier date.
            - The end_date can be set to a later date.
            - The is_active field can be set to True.
            - The name can change.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "updated_period",
            'start_date': timezone.now() + timedelta(weeks=1),
            'price': '2000.00',
        }

        response = self.client.patch(
            reverse(
                'period-detail',
                args=[self.period_active.id]
            ),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "The period contains timeslots with user reservations."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_partial_overlapping(self):
        """
        Ensure we can't partially update an active period if it overlaps with
        another active period.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "updated_period",
            'start_date': timezone.now() + timedelta(weeks=1),
            'price': '2000.00',
            'is_active': True,
        }

        response = self.client.patch(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'An active period associated to the same workplace overlaps '
                'with the provided start_date and end_date.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete(self):
        """
        Ensure we can delete a period that has no reservations.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_with_reservations(self):
        """
        Ensure we can delete a period that has reservations.
        """
        self.client.force_authenticate(user=self.admin)

        reservation_2 = Reservation.objects.create(
            user=self.user,
            timeslot=self.time_slot_active,
            is_active=True,
        )

        data = {
            'force_delete': True,
        }

        response = self.client.delete(
            reverse(
                'period-detail',
                args=[self.period_active.id]
            ),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.reservation.refresh_from_db()
        self.user.refresh_from_db()
        self.admin.refresh_from_db()

        # Make sure the timeslot was deleted (cascade)
        self.assertFalse(
            TimeSlot.objects.filter(
                pk=self.time_slot_active.pk
            ).exists()
        )
        self.assertFalse(self.reservation.is_active)
        self.assertEqual(self.reservation.cancelation_reason, 'TD')
        self.assertTrue(self.reservation.cancelation_date)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.user.tickets, 3)
        self.assertEqual(self.admin.tickets, 1)

        self.reservation.is_active = True
        self.reservation.cancelation_date = None
        self.reservation.cancelation_reason = None
        self.reservation.save()
        self.reservation.refresh_from_db()
        reservation_2.delete()
        self.user.tickets = 0
        self.user.save()
        self.admin.tickets = 0
        self.admin.save()

    def test_delete_with_reservations_no_force(self):
        """
        Ensure we can't delete a period that has reservations if the
        force_delete field is not provided and set to True.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            # 'force_delete': True,
        }

        response = self.client.delete(
            reverse(
                'period-detail',
                args=[self.period_active.id]
            ),
            data,
            format='json',
        )

        content = {
            "non_field_errors": [
                "Trying to do a Period deletion that affects "
                "users without providing `force_delete` field set to True."
            ]
        }

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(json.loads(response.content), content)

    def test_delete_with_reservations_invalid_force_delete(self):
        """
        Ensure we can't delete a timeslot that has reservations if the
        force_delete field is not provided and set to True.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'force_delete': "invalid",
        }

        response = self.client.delete(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
            data,
            format='json',
        )

        content = {
            'force_delete': [
                'Must be a valid boolean.'
            ]
        }

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(json.loads(response.content), content)

    def test_list(self):
        """
        Ensure we can list active periods as an unauthenticated user if is
        active.
        """
        response = self.client.get(
            reverse('period-list'),
            format='json',
        )

        data = json.loads(response.content)
        data['results'] = [
            remove_translation_fields(m) for m in data['results']
        ]

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.period_active.id,
                'end_date': data['results'][0]['end_date'],
                'is_active': True,
                'name': 'random_period_active',
                'price': '3.00',
                'total_reservations': 1,
                'start_date': data['results'][0]['start_date'],
                'url': f'http://testserver/periods/{self.period_active.id}',
                'workplace': f'http://testserver/workplaces/'
                f'{self.workplace.id}'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_list_date_filter(self):
        """
        Ensure we can list periods as admin with date filter
        """
        client = APIClient()
        client.force_authenticate(user=self.admin)

        period1 = Period.objects.create(
            name="current_period",
            workplace=self.workplace,
            start_date='2100-01-01T00:00:00Z',
            end_date='2100-01-03T00:00:00Z',
            price=3,
            is_active=False,
        )
        period2 = Period.objects.create(
            name="random_period2",
            workplace=self.workplace,
            start_date='2100-01-03T00:00:00Z',
            end_date='2100-01-05T00:00:00Z',
            price=3,
            is_active=False,
        )

        response = client.get(
            reverse('period-list'),
            {
                'start_date__lte': '2100-01-02T00:00:00Z',
                'end_date__gte': '2100-01-02T00:00:00Z',
            },
            format='json',
        )

        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], period1.name)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_inactive(self):
        """
        Ensure we can list all periods as an admin user.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('period-list'),
            format='json',
        )

        data = json.loads(response.content)
        data['results'] = [
            remove_translation_fields(m) for m in data['results']
        ]

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.period.id,
                'end_date': data['results'][0]['end_date'],
                'is_active': False,
                'name': 'random_period',
                'price': '3.00',
                'total_reservations': 0,
                'start_date': data['results'][0]['start_date'],
                'url': f'http://testserver/periods/{self.period.id}',
                'workplace':
                    f'http://testserver/workplaces/{self.workplace.id}'
            }, {
                'id': self.period_active.id,
                'end_date': data['results'][1]['end_date'],
                'is_active': True,
                'name': 'random_period_active',
                'price': '3.00',
                'total_reservations': 1,
                'start_date': data['results'][1]['start_date'],
                'url': f'http://testserver/periods/{self.period_active.id}',
                'workplace':
                    f'http://testserver/workplaces/{self.workplace.id}'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a period as an unauthenticated user if it is active.
        """

        response = self.client.get(
            reverse(
                'period-detail',
                args=[self.period_active.id]
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': self.period_active.id,
            'end_date': data['end_date'],
            'is_active': True,
            'name': 'random_period_active',
            'price': '3.00',
            'total_reservations': 1,
            'start_date': data['start_date'],
            'url': f'http://testserver/periods/{self.period_active.id}',
            'workplace': f'http://testserver/workplaces/{self.workplace.id}'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive(self):
        """
        Ensure we can read a period as admin if it is inactive.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': self.period.id,
            'end_date': data['end_date'],
            'is_active': False,
            'name': 'random_period',
            'price': '3.00',
            'total_reservations': 0,
            'start_date': data['start_date'],
            'url': f'http://testserver/periods/{self.period.id}',
            'workplace': f'http://testserver/workplaces/{self.workplace.id}'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_inactive_non_admin(self):
        """
        Ensure we can't read a period as non_admin if it is inactive.
        """

        response = self.client.get(
            reverse(
                'period-detail',
                args=[self.period.id]
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a period that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'period-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
