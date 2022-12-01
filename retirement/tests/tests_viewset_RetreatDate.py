import pytz
from unittest.mock import patch
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cron_manager.models import Task
from blitz_api.cron_manager_api import CronManager
from blitz_api.factories import (
    AdminFactory,
    UserFactory,
)
from blitz_api.testing_tools import (
    CustomAPITestCase,
)


from retirement.models import (
    RetreatType,
    RetreatDate,
    Retreat,
    AutomaticEmail,
    Reservation,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatDateTests(CustomAPITestCase):

    @classmethod
    def setUpClass(cls):
        super(RetreatDateTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.auto_email_before_start = AutomaticEmail.objects.create(
            retreat_type=self.retreatType,
            minutes_delta=1,
            template_id=1,
            time_base=AutomaticEmail.TIME_BASE_BEFORE_START

        )
        self.auto_email_after_start = AutomaticEmail.objects.create(
            retreat_type=self.retreatType,
            minutes_delta=1,
            template_id=2,
            time_base=AutomaticEmail.TIME_BASE_AFTER_END
        )
        self.retreat = Retreat.objects.create(
            name="mega retreat",
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
            activity_language='FR',
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
        self.rd1 = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2100, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2100, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.rd2 = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.rd3 = RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2230, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2230, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()
        self.cron_manager = CronManager()

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        self.task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        self.task_after = Task.objects.get(url=task_url, active=True)

    def test_update_as_user(self):
        """
        Ensure user can't update retreat date
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd1.id},
            ),
            {'data': 'test'},
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_delete_as_user(self):
        """
        Ensure user can't delete retreat date
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd1.id},
            ),
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_update_no_message_as_admin(self):
        """
        Test that updating a date without message but with registered
         user trigger error
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        data = {
            'start_time': LOCAL_TIMEZONE.localize(datetime(2131, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2132, 1, 17, 12)),
        }
        response = self.client.patch(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_update_no_change_as_admin(self, mock_email, mock_cancel):
        """
        Test that updating a date that doesn't impact start or end
        notify the user but doesn't change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'start_time': LOCAL_TIMEZONE.localize(datetime(2131, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2132, 1, 17, 12)),
            'reason_message': reason_message,
        }
        response = self.client.patch(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertEqual(self.task_after, task_after)
        self.assertEqual(self.task_before, task_before)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_update_change_after_as_admin(self, mock_email, mock_cancel):
        """
        Test that updating a date that do impact end
        notify the user and change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'start_time': LOCAL_TIMEZONE.localize(datetime(2400, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2400, 1, 17, 12)),
            'reason_message': reason_message,
        }
        response = self.client.patch(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertNotEqual(self.task_after, task_after)
        self.assertEqual(self.task_before, task_before)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_update_change_before_as_admin(self, mock_email, mock_cancel):
        """
        Test that updating a date that do impact start
        notify the user and change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'start_time': LOCAL_TIMEZONE.localize(datetime(2099, 1, 15, 8)),
            'end_time': LOCAL_TIMEZONE.localize(datetime(2099, 1, 17, 12)),
            'reason_message': reason_message,
        }
        response = self.client.patch(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertEqual(self.task_after, task_after)
        self.assertNotEqual(self.task_before, task_before)

    def test_delete_no_message_as_admin(self):
        """
        Test that deleting a date without message but with registered
         user trigger error
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_delete_no_change_as_admin(self, mock_email, mock_cancel):
        """
        Test that deleting a date that doesn't impact start or end
        notify the user but doesn't change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'reason_message': reason_message,
        }
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertEqual(self.task_after, task_after)
        self.assertEqual(self.task_before, task_before)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_delete_change_after_as_admin(self, mock_email, mock_cancel):
        """
        Test that deleting a date that impact end
        notify the user and change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'reason_message': reason_message,
        }
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd3.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertNotEqual(self.task_after, task_after)
        self.assertEqual(self.task_before, task_before)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_delete_change_before_as_admin(self, mock_email, mock_cancel):
        """
        Test that deleting a date that impact start
        notify the user and change the auto email
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'reason_message': reason_message,
        }
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd1.id},
            ),
            data,
            format='json',
        )

        mock_email.assert_called_once_with(
            self.retreat,
            self.retreat.get_participants_emails(),
            reason_message,
            'update'
        )
        mock_cancel.assert_called_once_with(False)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_before_start)
        task_before = Task.objects.get(url=task_url, active=True)

        task_url = self.cron_manager.get_retreat_target_url(
            self.retreat, self.auto_email_after_start)
        task_after = Task.objects.get(url=task_url, active=True)

        self.assertEqual(self.task_after, task_after)
        self.assertNotEqual(self.task_before, task_before)

    @patch('retirement.models.Retreat.cancel_participants_reservation')
    @patch('retirement.services.send_updated_retreat_email')
    def test_delete_all_retreat_as_admin(self, mock_email, mock_cancel):
        """
        Test that deleting all dates is not possible
        """
        self.client.force_authenticate(user=self.admin)
        user = UserFactory()
        Reservation.objects.create(
            user=user,
            retreat=self.retreat,
            is_active=True,
        )
        reason_message = 'blabla'
        data = {
            'reason_message': reason_message,
        }
        self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd1.id},
            ),
            data,
            format='json',
        )
        self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd2.id},
            ),
            data,
            format='json',
        )
        response = self.client.delete(
            reverse(
                'retreat:retreatdate-detail',
                kwargs={'pk': self.rd3.id},
            ),
            data,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
