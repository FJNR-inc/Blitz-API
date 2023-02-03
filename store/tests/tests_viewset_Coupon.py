import json
import pytz
from datetime import (
    datetime,
    timedelta,
)
from rest_framework import status
from rest_framework.test import (
    APIClient,
    APITestCase,
)
from unittest import mock
from django.conf import settings
from django.core import mail
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from blitz_api.factories import (
    UserFactory,
    AdminFactory,
    CouponFactory,
)
from blitz_api.testing_tools import CustomAPITestCase
from workplace.models import (
    TimeSlot,
    Period,
    Workplace,
)
from retirement.models import (
    Retreat,
    RetreatType,
    RetreatDate,
)
from store.models import (
    Package,
    Membership,
    Coupon,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class CouponTests(CustomAPITestCase):

    ATTRIBUTES = [
        'url',
        'id',
        'value',
        'percent_off',
        'code',
        'start_time',
        'end_time',
        'max_use',
        'max_use_per_user',
        'details',
        'owner',
        'organization',
        'applicable_product_types',
        'applicable_memberships',
        'applicable_packages',
        'applicable_retreats',
        'applicable_retreat_types',
        'applicable_timeslots',
        'users',
        'usages',
        'is_applicable_to_physical_retreat',
        'is_applicable_to_virtual_retreat',
    ]

    @classmethod
    def setUpClass(cls):
        super(CouponTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        cls.period = Period.objects.create(
            name="random_period_active",
            workplace=cls.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        cls.time_slot = TimeSlot.objects.create(
            period=cls.period,
            price=1,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        cls.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        cls.retreat = Retreat.objects.create(
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
                datetime(2130, 1, 15, 8),
            ),
            type=cls.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=cls.retreat,
        )
        cls.retreat.activate()
        cls.coupon = Coupon.objects.create(
            value=13,
            code="ABCDEFGH",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=cls.user,
        )
        cls.coupon2 = Coupon.objects.create(
            value=13,
            code="ABCD1234",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=cls.admin,
        )
        cls.coupon.applicable_product_types.add(cls.package_type)

        cls.maxDiff = None

    def test_create(self):
        """
        Ensure we can create a coupon if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        content = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "percent_off": None,
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.assertEqual(
            response_data,
            content
        )

    def test_create_choose_code(self):
        """
        Ensure we can create a coupon if user has permission.
        Ensure that the user can choose the code (regex-validated).
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "code": "1234ABCD",
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        content = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "percent_off": None,
            "code": "1234ABCD",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.assertEqual(
            response_data,
            content
        )

    def test_create_percentage(self):
        """
        Ensure we can create a coupon if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "percent_off": "80",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        content = {
            "applicable_product_types": [
                "package"
            ],
            "value": None,
            "percent_off": 80,
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.assertEqual(
            response_data,
            content
        )

    def test_create_percentage_and_value(self):
        """
        Ensure we can create a coupon if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "percent_off": "80",
            "value": "150.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        content = {
            'non_field_errors': [
                "You can't set a discount value (value) and a discount "
                "percentage (percent_off) at the same time."
            ]
        }

        self.assertEqual(
            json.loads(response.content),
            content
        )

    def test_create_no_percentage_or_value(self):
        """
        Ensure we can create a coupon if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        content = {
            'non_field_errors': [
                "You need to set a value discount (value) or a discount "
                "percentage (percent_off) for this coupon."
            ]
        }

        self.assertEqual(
            json.loads(response.content),
            content
        )

    def test_notify_email_for_coupon(self):
        """
        Ensure that an admin can notify a list of emails.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "email_list": [
                "fake@fake.com",
                "whatever@whatever.com",
            ]
        }

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content,
        )

        self.assertEqual(len(mail.outbox), 2)

    def test_notify_email_for_coupon_owner(self):
        """
        Ensure that a coupon owner can notify a list of emails.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            "email_list": [
                "fake@fake.com",
                "whatever@whatever.com",
            ]
        }

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
            response.content,
        )

        self.assertEqual(len(mail.outbox), 2)

    def test_notify_email_for_coupon_random_user(self):
        """
        Ensure that a random authenticated user can't notify for coupon.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            "email_list": [
                "fake@fake.com",
                "whatever@whatever.com",
            ]
        }

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': 2},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "detail": "Not found."
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
            response.content,
        )

        self.assertEqual(content, response_data)

        self.assertEqual(len(mail.outbox), 0)

    def test_notify_email_for_coupon_missing_field(self):
        """
        Ensure that an admin can't notify a list of emails if the list is
        missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "email_list": ["This field is required."]
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        self.assertEqual(content, response_data)

        self.assertEqual(len(mail.outbox), 0)

    def test_notify_email_for_coupon_invalid_email(self):
        """
        Ensure that an admin can't notify a list of emails if the list contains
        invalid email addresses.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "email_list": [
                "invalid",
                "fake@fake.com"
            ]
        }

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "email_list": ["Enter a valid email address."]
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        self.assertEqual(content, response_data)

        self.assertEqual(len(mail.outbox), 0)

    def test_notify_email_for_coupon_invalid_field(self):
        """
        Ensure that an admin can't notify a list of emails if the email_list
        field is invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "email_list": "invalid"
        }

        response = self.client.post(
            reverse(
                'coupon-notify',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "email_list": ['Expected a list of items but got type "str".']
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        self.assertEqual(content, response_data)

        self.assertEqual(len(mail.outbox), 0)

    def test_create_too_many(self):
        """
        Ensure we can't create a coupon if the API can't generate an unused
        code.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }
        with mock.patch(
                'store.serializers.random.choices', return_value="ABCDEFGH"):
            response = self.client.post(
                reverse('coupon-list'),
                data,
                format='json',
            )

        content = {
            'non_field_errors': [
                "Can't generate new unique codes. Delete old coupons."
            ]
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        self.assertEqual(
            json.loads(response.content),
            content
        )

    def test_create_without_permission(self):
        """
        Ensure we can't create a coupon if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_missing_field(self):
        """
        Ensure we can't create a coupon when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            "start_time": [
                "This field is required."
            ],
            "end_time": [
                "This field is required."
            ],
            "max_use": [
                "This field is required."
            ],
            "max_use_per_user": [
                "This field is required."
            ],
            "owner": [
                "This field is required."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create a coupon when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "value": None,
            "percent_off": None,
            "start_time": None,
            "end_time": None,
            "max_use": None,
            "max_use_per_user": None,
            "owner": None,
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            "start_time": [
                "This field may not be null."
            ],
            "percent_off": [
                "This field may not be null."
            ],
            "value": [
                "This field may not be null."
            ],
            "end_time": [
                "This field may not be null."
            ],
            "max_use": [
                "This field may not be null."
            ],
            "max_use_per_user": [
                "This field may not be null."
            ],
            "owner": [
                "This field may not be null."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a coupon when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "value": (1,),
            "percent_off": (1,),
            "start_time": (1,),
            "end_time": (1,),
            "max_use": (1,),
            "max_use_per_user": (1,),
            "owner": (1,),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            "value": [
                "A valid number is required."
            ],
            "percent_off": [
                "A valid integer is required."
            ],
            "start_time": [
                "Datetime has wrong format. Use one of these formats instead:"
                " YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."
            ],
            "end_time": [
                "Datetime has wrong format. Use one of these formats instead:"
                " YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z]."
            ],
            "max_use": [
                "A valid integer is required."
            ],
            "max_use_per_user": [
                "A valid integer is required."
            ],
            "owner": [
                'Incorrect type. Expected URL string, received list.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_negative_values(self):
        """
        Ensure we can't create a coupon with negative values.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "value": "-13.00",
            "percent_off": "-13",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": -100,
            "max_use_per_user": -2,
            "details": "Any package for fjeanneau clients",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            "value": [
                "Ensure this value is greater than or equal to 0.0."
            ],
            "percent_off": [
                "Ensure this value is greater than or equal to 0."
            ],
            "max_use": [
                "Ensure this value is greater than or equal to 0."
            ],
            "max_use_per_user": [
                "Ensure this value is greater than or equal to 0."
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a coupon.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
            "owner": "http://testserver/users/" + str(self.user.id),
        }

        response = self.client.put(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/" + str(self.coupon.id),
            "id": self.coupon.id,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "percent_off": None,
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            response_data,
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial(self):
        """
        Ensure we can partially update a coupon.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
        }

        response = self.client.patch(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/" + str(self.coupon.id),
            "id": self.coupon.id,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "percent_off": None,
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            response_data,
            content
        )

    def test_delete_as_admin(self):
        """
        Ensure we can delete a coupon.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )

    def test_delete_as_user(self):
        """
        Ensure that a user can't delete a coupon.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN
        )

    def test_delete_inexistent(self):
        """
        Ensure that deleting a non-existent coupon does nothing.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'coupon-detail',
                kwargs={'pk': 999},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )

    def test_list(self):
        """
        Ensure we can list owned coupons as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        self.coupon.applicable_retreats.set([
            self.retreat,
        ])
        self.coupon.applicable_retreat_types.set([
            self.retreat.type,
        ])
        self.coupon.applicable_timeslots.set([
            self.time_slot,
        ])
        self.coupon.applicable_packages.set([
            self.package,
        ])
        self.coupon.applicable_memberships.set([
            self.membership,
        ])

        response = self.client.get(
            reverse('coupon-list'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = json.loads(response.content)
        for item in content['results']:
            self.check_attributes(item)

        self.coupon.applicable_retreats.set([])
        self.coupon.applicable_retreat_types.set([])
        self.coupon.applicable_timeslots.set([])
        self.coupon.applicable_packages.set([])
        self.coupon.applicable_memberships.set([])

    def test_list_as_admin(self):
        """
        Ensure we can list all coupons as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('coupon-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                "url": "http://testserver/coupons/" + str(self.coupon.id),
                "id": self.coupon.id,
                "applicable_product_types": [
                    "package"
                ],
                "value": "13.00",
                "percent_off": None,
                "code": data['results'][0]['code'],
                "start_time": "2019-01-06T15:11:05-05:00",
                "end_time": "2020-01-06T15:11:06-05:00",
                "max_use": 100,
                "max_use_per_user": 2,
                "details": "Any package for clients",
                "owner": "http://testserver/users/" + str(self.user.id),
                "organization": None,
                "applicable_retreats": [],
                "applicable_retreat_types": [],
                "applicable_timeslots": [],
                "applicable_packages": [],
                "applicable_memberships": [],
                "users": [],
                "usages": [],
                "is_applicable_to_physical_retreat": False,
                "is_applicable_to_virtual_retreat": False
            }, {
                "url": "http://testserver/coupons/" + str(self.coupon2.id),
                "id": self.coupon2.id,
                "applicable_product_types": [],
                "value": "13.00",
                "percent_off": None,
                "code": data['results'][1]['code'],
                "start_time": "2019-01-06T15:11:05-05:00",
                "end_time": "2020-01-06T15:11:06-05:00",
                "max_use": 100,
                "max_use_per_user": 2,
                "details": "Any package for clients",
                "owner": "http://testserver/users/" + str(self.admin.id),
                "organization": None,
                "applicable_retreats": [],
                "applicable_retreat_types": [],
                "applicable_timeslots": [],
                "applicable_packages": [],
                "applicable_memberships": [],
                "users": [],
                "usages": [],
                "is_applicable_to_physical_retreat": False,
                "is_applicable_to_virtual_retreat": False
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_search_by_code(self):
        """
        Ensure we can list all coupons matching a search.
        """
        self.client.force_authenticate(user=self.admin)
        c1 = CouponFactory(code='my search Rom', owner=self.user)
        c2 = CouponFactory(code='my search Rom2', owner=self.user)
        c3 = CouponFactory(code='completely different', owner=self.user)
        c4 = CouponFactory(code='another different code', owner=self.user)

        response = self.client.get(
            reverse('coupon-list'),
            {
                'search': 'Rom'
            },
            format='json',
        )

        data = json.loads(response.content)
        coupon_ids = [coupon['id'] for coupon in data['results']]
        self.assertEqual(len(data['results']), 2)
        self.assertTrue(c1.id in coupon_ids)
        self.assertTrue(c2.id in coupon_ids)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            reverse('coupon-list'),
            {
                'search': 'owopwehpweihwpei'
            },
            format='json',
        )

        data = json.loads(response.content)
        self.assertEqual(len(data['results']), 0)

    def test_read(self):
        """
        Ensure we can read a coupon as an authenticated user.
        Ensure we get a nested repr for applicable_* fields.
        """
        self.client.force_authenticate(user=self.user)

        self.coupon.applicable_retreats.set([
            self.retreat,
        ])
        self.coupon.applicable_timeslots.set([
            self.time_slot,
        ])
        self.coupon.applicable_packages.set([
            self.package,
        ])
        self.coupon.applicable_memberships.set([
            self.membership,
        ])

        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.pk},
            ),
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.check_attributes(content)

        self.coupon.applicable_retreats.set([])
        self.coupon.applicable_timeslots.set([])
        self.coupon.applicable_packages.set([])
        self.coupon.applicable_memberships.set([])

    def test_read_admin(self):
        """
        Ensure we can read any coupon as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/" + str(self.coupon.id),
            "id": self.coupon.id,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "percent_off": None,
            "code": data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/" + str(self.user.id),
            "organization": None,
            "applicable_retreats": [],
            "applicable_retreat_types": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": [],
            "usages": [],
            "is_applicable_to_physical_retreat": False,
            "is_applicable_to_virtual_retreat": False
        }

        self.assertEqual(
            data,
            content
        )

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a coupon that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_not_authenticated(self):
        """
        Ensure we can't get coupons if not authenticated.
        """
        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': self.coupon.id},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
