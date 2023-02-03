import json

from datetime import timedelta
from unittest import mock

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.test.utils import override_settings

from ..factories import UserFactory, AdminFactory
from ..models import (ActionToken, Organization, Domain,
                      AcademicField, AcademicLevel)
from ..services import remove_translation_fields
from store.models import (
    Membership,
)

from ..testing_tools import CustomAPITestCase

User = get_user_model()


class UsersTests(CustomAPITestCase):

    @classmethod
    def setUpClass(cls):
        super(UsersTests, cls).setUpClass()
        org = Organization.objects.create(name="random_university")
        Domain.objects.create(
            name="mailinator.com",
            organization_id=org.id
        )
        AcademicField.objects.create(name="random_field")
        cls.academic_level = AcademicLevel.objects.create(name="random_level")
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        cls.membership.academic_levels.set([cls.academic_level])

    def setUp(self):
        self.client = APIClient()

        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.membership = self.membership
        self.user.save()

        self.admin = AdminFactory()
        self.admin.set_password('Test123!')
        self.admin.save()

    def test_create_new_student_user(self):
        """
        Ensure we can create a new user if we have the permission.
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                'name': "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['phone'], '1234567890')

        user = User.objects.get(email="John@mailinator.com")
        activation_token = ActionToken.objects.filter(
            user=user,
            type='account_activation',
        )

        self.assertEqual(1, len(activation_token))

    def test_create_new_user(self):
        """
        Ensure we can create a new user if we have the permission.
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['phone'], '1234567890')

        user = User.objects.get(email="John@mailinator.com")
        activation_token = ActionToken.objects.filter(
            user=user,
            type='account_activation',
        )

        self.assertEqual(1, len(activation_token))

    def test_create_new_student_user_missing_field(self):
        """
        Ensure we can't create a student user without academic_* fields.
        """
        data = {
            'email': 'John@mailinator.com',
            'password': 'test123!',
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_new_user_blank_fields(self):
        """
        Ensure we can't create a new user with blank fields
        """
        self.maxDiff = None
        data = {
            'email': '',
            'password': '',
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {
            'email': ['This field may not be blank.'],
            'password': ['This field may not be blank.'],
        }
        self.assertEqual(json.loads(response.content), content)

    def test_create_new_user_missing_fields(self):
        """
        Ensure we can't create a new user without required fields
        """
        data = {}

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {
            'email': ['This field is required.'],
            'password': ['This field is required.']
        }
        self.assertEqual(json.loads(response.content), content)

    def test_create_new_user_weak_password(self):
        """
        Ensure we can't create a new user with a weak password
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': '19274682736',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {"password": ['This password is entirely numeric.']}
        self.assertEqual(json.loads(response.content), content)

    def test_create_new_user_invalid_phone(self):
        """
        Ensure we can't create a new user with an invalid phone number
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': '1fasd6dq#$%',
            'phone': '12345',
            'other_phone': '23445dfg',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {
            "phone": ['Invalid format.'],
            "other_phone": ['Invalid format.']
        }
        self.assertEqual(json.loads(response.content), content)

    def test_create_new_user_duplicate_email(self):
        """
        Ensure we can't create a new user with an already existing email
        """

        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        user = UserFactory()
        user.email = 'JOHN@mailinator.com'
        user.save()

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        content = {
            'email': [
                "An account for the specified email address already exists."
            ]
        }
        self.assertEqual(json.loads(response.content), content)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "AUTO_ACTIVATE_USER": False,
            "FRONTEND_INTEGRATION": {
                "ACTIVATION_URL": "fake_url",
            }
        }
    )
    def test_create_user_activation_email(self):
        """
        Ensure that the activation email is sent when user signs up.
        """

        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['phone'], '1234567890')

        user = User.objects.get(email="John@mailinator.com")
        activation_token = ActionToken.objects.filter(
            user=user,
            type='account_activation',
        )

        self.assertFalse(user.is_active)
        self.assertEqual(1, len(activation_token))

        # Test that one message was sent:
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "AUTO_ACTIVATE_USER": False,
            "FRONTEND_INTEGRATION": {
                "ACTIVATION_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.services.EmailMessage.send', return_value=0)
    def test_create_user_activation_email_failure(self, send):
        """
        Ensure that the user is notified that no email was sent.
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['phone'], '1234567890')

        user = User.objects.get(email="John@mailinator.com")
        activation_token = ActionToken.objects.filter(
            user=user,
            type='account_activation',
        )

        self.assertFalse(user.is_active)
        self.assertEqual(1, len(activation_token))

        # Test that no email was sent:
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "AUTO_ACTIVATE_USER": True,
            "FRONTEND_INTEGRATION": {
                "ACTIVATION_URL": "fake_url",
            }
        }
    )
    @mock.patch('blitz_api.services.EmailMessage.send', return_value=0)
    def test_create_user_auto_activate(self, services):
        """
        Ensure that the user is automatically activated.
        """
        data = {
            'username': 'John',
            'email': 'John@mailinator.com',
            'password': 'test123!',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        response = self.client.post(
            reverse('user-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(response.content)['phone'], '1234567890')

        user = User.objects.get(email="John@mailinator.com")
        activation_token = ActionToken.objects.filter(
            user=user,
            type='account_activation',
        )

        self.assertTrue(user.is_active)
        self.assertEqual(1, len(activation_token))

        # Test that no email was sent:
        self.assertEqual(len(mail.outbox), 0)

    def test_list_users(self):
        """
        Ensure we can list all users.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse('user-list'))
        self.assertEqual(json.loads(response.content)['count'], 2)

        # Users are ordered alphabetically by email
        first_user = json.loads(response.content)['results'][0]
        second_user = json.loads(response.content)['results'][1]
        self.assertEqual(first_user['email'], self.admin.email)

        membership = {
            'url': 'http://testserver/memberships/' + str(self.membership.id),
            'id': self.membership.id,
            'name': 'basic_membership',
            'available': True,
            'available_on_product_types': [],
            'available_on_products': [],
            'options': [],
            'picture': None,
            'price': '50.00',
            'details': '1-Year student membership',
            'duration': '365 00:00:00',
            'available_on_retreat_types': [],
            'academic_levels': ['http://testserver/academic_levels/' +
                                str(self.academic_level.id)]
        }

        self.assertEqual(
            remove_translation_fields(second_user['membership']),
            membership
        )

        # Check the system doesn't return attributes not expected
        attributes = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'university',
            'last_login',
            'date_joined',
            'academic_level',
            'academic_field',
            'gender',
            'language',
            'birthdate',
            'groups',
            'user_permissions',
            'tickets',
            'membership',
            'membership_end',
            'city',
            'personnal_restrictions',
            'academic_program_code',
            'faculty',
            'student_number',
            'volunteer_for_workplace',
            'hide_newsletter',
            'is_in_newsletter',
            'number_of_free_virtual_retreat',
            'membership_end_notification',
            'get_number_of_past_tomatoes',
            'get_number_of_future_tomatoes',
            'last_acceptation_terms_and_conditions',
            'tomato_field_matrix',
        ]
        for key in first_user.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users_with_search(self):
        """
        Ensure we can list all users.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(reverse('user-list') + '?search=chuck')
        self.assertEqual(json.loads(response.content)['count'], 1)

        # Users are ordered alphabetically by email
        first_user = json.loads(response.content)['results'][0]
        self.assertEqual(first_user['email'], self.admin.email)

        # Check the system doesn't return attributes not expected
        attributes = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'university',
            'last_login',
            'date_joined',
            'academic_level',
            'academic_field',
            'gender',
            'language',
            'birthdate',
            'groups',
            'user_permissions',
            'tickets',
            'membership',
            'membership_end',
            'city',
            'personnal_restrictions',
            'academic_program_code',
            'faculty',
            'student_number',
            'volunteer_for_workplace',
            'hide_newsletter',
            'is_in_newsletter',
            'number_of_free_virtual_retreat',
            'membership_end_notification',
            'get_number_of_past_tomatoes',
            'get_number_of_future_tomatoes',
            'last_acceptation_terms_and_conditions',
            'tomato_field_matrix',
        ]
        for key in first_user.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_users_without_authenticate(self):
        """
        Ensure we can't list users without authentication.
        """
        response = self.client.get(reverse('user-list'))

        content = {"detail": "Authentication credentials were not provided."}
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_without_permissions(self):
        """
        Ensure we can't list users without permissions.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('user-list'))

        content = {
            'detail': 'You do not have permission to perform this action.'
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
        }
    )
    def test_send_notification_end_membership(self):
        """
        Ensure we can send notification for membership end
        """

        fixed_time = timezone.now()

        end_time_membership = fixed_time + relativedelta(days=28)

        self.user.membership = self.membership
        self.user.membership_end = end_time_membership
        self.user.save()

        with mock.patch(
                'store.serializers.timezone.now',
                return_value=fixed_time
        ):
            response = self.client.get(
                reverse('user-execute-automatic-email-membership-end')
            )

        content = {
            'stop': False,
            'email_send_count': 1
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            json.loads(response.content),
            content
        )

        self.assertEqual(len(mail.outbox), 1)

        self.user.refresh_from_db()
        self.assertEqual(self.user.membership_end_notification, fixed_time)

        with mock.patch(
                'store.serializers.timezone.now',
                return_value=fixed_time
        ):
            response = self.client.get(
                reverse('user-execute-automatic-email-membership-end')
            )
        content = {
            'stop': False,
            'email_send_count': 0
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            json.loads(response.content),
            content
        )

        # no new mail
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        LOCAL_SETTINGS={
            "EMAIL_SERVICE": True,
            "FRONTEND_INTEGRATION": {
                'ACTIVATION_URL': 'https://example.com/activate/{{token}}'
            }
        }
    )
    def test_resend_activation_email(self):
        """
        Ensure we can resend an activation email on demand
        """

        data = {
            'email': self.user.email,
        }

        response = self.client.post(
            reverse('user-resend-activation-email'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            response.content,
            b'',
        )

        self.assertEqual(len(mail.outbox), 1)

    def test_credit_ticket_as_admin(self):
        """
        Ensure admin can credit tickets to a user
        """
        user = UserFactory()
        self.assertEqual(user.tickets, 1)
        nb_tickets_to_add = 5
        data = {
            'nb_tickets': nb_tickets_to_add,
        }

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse(
                'user-credit-tickets',
                kwargs={'pk': user.id},
            ),
            data,
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            User.objects.get(pk=user.id).tickets,
            1 + nb_tickets_to_add
        )

    def test_credit_ticket_as_user(self):
        """
        Ensure user can't credit tickets to a user
        """
        user = UserFactory()
        self.assertEqual(user.tickets, 1)
        nb_tickets_to_add = 5
        data = {
            'nb_tickets': nb_tickets_to_add,
        }

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            reverse(
                'user-credit-tickets',
                kwargs={'pk': user.id},
            ),
            data,
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_credit_ticket_not_int(self):
        """
        Ensure admin can't credit invalid tickets to a user
        """
        user = UserFactory()
        self.assertEqual(user.tickets, 1)
        nb_tickets_to_add = 'this is not an int'
        data = {
            'nb_tickets': nb_tickets_to_add,
        }

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse(
                'user-credit-tickets',
                kwargs={'pk': user.id},
            ),
            data,
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_credit_ticket_negative_int(self):
        """
        Ensure admin can't credit negative tickets to a user
        """
        user = UserFactory()
        self.assertEqual(user.tickets, 1)
        nb_tickets_to_add = -5
        data = {
            'nb_tickets': nb_tickets_to_add,
        }

        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse(
                'user-credit-tickets',
                kwargs={'pk': user.id},
            ),
            data,
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
