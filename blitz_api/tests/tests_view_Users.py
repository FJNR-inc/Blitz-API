import json
import pytz

from datetime import timedelta, datetime
from unittest import mock

from dateutil.relativedelta import relativedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.urls import reverse
from django.test.utils import override_settings
from django.conf import settings

from ..factories import UserFactory, AdminFactory
from ..models import (ActionToken, Organization, Domain,
                      AcademicField, AcademicLevel)
from ..services import remove_translation_fields
from store.models import (
    Membership,
    Order,
    OrderLine,
    OrderLineBaseProduct,
    OptionProduct,
    Coupon,
)
from retirement.models import (
    Retreat,
    RetreatType,
)
from blitz_api import testing_tools
from ..testing_tools import CustomAPITestCase

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)

User = get_user_model()


class UsersTests(CustomAPITestCase):
    ORDER_ATTRIBUTES = testing_tools.ORDER_HISTORY_ATTRIBUTES
    ORDERLINE_ATTRIBUTES = testing_tools.ORDERLINE_ATTRIBUTES
    OPTION_ATTRIBUTES = testing_tools.OPTION_ATTRIBUTES

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

        self.retreat_content_type = ContentType.objects.get_for_model(Retreat)
        self.membership_type = ContentType.objects.get_for_model(Membership)
        self.coupon = Coupon.objects.create(
            value=13,
            code="ABCDEFGH",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2030-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=self.user,
        )
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            seats=400,
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        self.options_1: OptionProduct = OptionProduct.objects.create(
            name="options_1",
            details="options_1",
            available=True,
            price=50.00,
            max_quantity=10,
        )
        self.options_1.available_on_products.add(self.retreat)
        self.options_2: OptionProduct = OptionProduct.objects.create(
            name="options_2",
            details="options_2",
            available=True,
            price=150.00,
            max_quantity=10,
        )
        self.options_2.available_on_products.add(self.retreat)
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
            cost=self.retreat.price
        )
        OrderLineBaseProduct.objects.create(
            order_line=self.order_line,
            option=self.options_1,
            quantity=3
        )
        OrderLineBaseProduct.objects.create(
            order_line=self.order_line,
            option=self.options_2,
            quantity=2
        )
        self.order_line_2 = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.membership_type,
            object_id=self.membership.id,
            cost=self.membership.price,
            coupon=self.coupon
        )

        self.order2 = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order2,
            quantity=1,
            content_type=self.membership_type,
            object_id=self.membership.id,
            cost=self.membership.price,
        )

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

    def test_user_order_history(self):
        """
        Ensure user can get own order history
        """

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse(
                'user-order-history',
                kwargs={'pk': self.user.id},
            ),
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )
        content = json.loads(response.content)
        self.assertEqual(len(content), 2)
        self.check_attributes(content[0], self.ORDER_ATTRIBUTES)
        self.check_attributes(
            content[0]['order_lines'][0], self.ORDERLINE_ATTRIBUTES)
        self.check_attributes(
            content[0]['order_lines'][0]['options'][0], self.OPTION_ATTRIBUTES
        )

    def test_admin_order_history(self):
        """
        Ensure admin can get a user order history
        """

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse(
                'user-order-history',
                kwargs={'pk': self.user.id},
            ),
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )
        content = json.loads(response.content)
        self.assertEqual(len(content), 2)
        self.check_attributes(content[0], self.ORDER_ATTRIBUTES)
        self.check_attributes(
            content[0]['order_lines'][0], self.ORDERLINE_ATTRIBUTES)
        self.check_attributes(
            content[0]['order_lines'][0]['options'][0], self.OPTION_ATTRIBUTES
        )

    def test_no_owner_order_history(self):
        """
        Ensure we can get a user order history
        """
        user_2 = UserFactory()
        self.client.force_authenticate(user=user_2)
        response = self.client.get(
            reverse(
                'user-order-history',
                kwargs={'pk': self.user.id},
            ),
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            response.content
        )
