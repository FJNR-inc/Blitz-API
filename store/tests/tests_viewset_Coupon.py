import json

from datetime import timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from unittest import mock

from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.models import AcademicLevel
from blitz_api.services import remove_translation_fields

from ..models import Package, Order, OrderLine, Membership, Coupon

User = get_user_model()


class CouponTests(APITestCase):

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
            code="ABCDEFGH",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for clients",
            owner=cls.admin,
        )
        cls.coupon.applicable_product_types.add(cls.package_type)

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
            "owner": "http://testserver/users/1",
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/3",
            "id": 3,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/1",
            "applicable_retirements": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": []
        }

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.assertEqual(
            json.loads(response.content),
            content
        )

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
            "owner": "http://testserver/users/1",
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
            "owner": "http://testserver/users/1",
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
            "value": [
                "This field is required."
            ],
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
            "value": [
                "This field may not be null."
            ],
            "start_time": [
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
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": -100,
            "max_use_per_user": -2,
            "details": "Any package for fjeanneau clients",
            "owner": "http://testserver/users/1",
        }

        response = self.client.post(
            reverse('coupon-list'),
            data,
            format='json',
        )

        content = {
            "value": [
                "Ensure this value is greater than or equal to 0.1."
            ],
            "max_use": [
                "Ensure this value is greater than or equal to 1."
            ],
            "max_use_per_user": [
                "Ensure this value is greater than or equal to 1."
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
            "owner": "http://testserver/users/1",
        }

        response = self.client.put(
            reverse(
                'coupon-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/1",
            "id": 1,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
            "owner": "http://testserver/users/1",
            "applicable_retirements": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": []
        }

        self.assertEqual(
            response_data,
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial(self):
        """
        Ensure we can partially update a package.
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
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/1",
            "id": 1,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "code": response_data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 1000,
            "max_use_per_user": 20,
            "details": "Any package for clients (updated max_use)",
            "owner": "http://testserver/users/1",
            "applicable_retirements": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": []
        }

        self.assertEqual(
            response_data,
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_as_admin(self):
        """
        Ensure we can delete a coupon.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'coupon-detail',
                kwargs={'pk': 1},
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
                kwargs={'pk': 1},
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

        response = self.client.get(
            reverse('coupon-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                "url": "http://testserver/coupons/1",
                "id": 1,
                "applicable_product_types": [
                    "package"
                ],
                "value": "13.00",
                "code": data['results'][0]['code'],
                "start_time": "2019-01-06T15:11:05-05:00",
                "end_time": "2020-01-06T15:11:06-05:00",
                "max_use": 100,
                "max_use_per_user": 2,
                "details": "Any package for clients",
                "owner": "http://testserver/users/1",
                "applicable_retirements": [],
                "applicable_timeslots": [],
                "applicable_packages": [],
                "applicable_memberships": [],
                "users": []
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

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
                "url": "http://testserver/coupons/1",
                "id": 1,
                "applicable_product_types": [
                    "package"
                ],
                "value": "13.00",
                "code": data['results'][0]['code'],
                "start_time": "2019-01-06T15:11:05-05:00",
                "end_time": "2020-01-06T15:11:06-05:00",
                "max_use": 100,
                "max_use_per_user": 2,
                "details": "Any package for clients",
                "owner": "http://testserver/users/1",
                "applicable_retirements": [],
                "applicable_timeslots": [],
                "applicable_packages": [],
                "applicable_memberships": [],
                "users": []
            }, {
                "url": "http://testserver/coupons/2",
                "id": 2,
                "applicable_product_types": [],
                "value": "13.00",
                "code": data['results'][1]['code'],
                "start_time": "2019-01-06T15:11:05-05:00",
                "end_time": "2020-01-06T15:11:06-05:00",
                "max_use": 100,
                "max_use_per_user": 2,
                "details": "Any package for clients",
                "owner": "http://testserver/users/2",
                "applicable_retirements": [],
                "applicable_timeslots": [],
                "applicable_packages": [],
                "applicable_memberships": [],
                "users": []
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a coupon as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/1",
            "id": 1,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "code": data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/1",
            "applicable_retirements": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": []
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_admin(self):
        """
        Ensure we can read any coupon as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'coupon-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        data = json.loads(response.content)

        content = {
            "url": "http://testserver/coupons/1",
            "id": 1,
            "applicable_product_types": [
                "package"
            ],
            "value": "13.00",
            "code": data['code'],
            "start_time": "2019-01-06T15:11:05-05:00",
            "end_time": "2020-01-06T15:11:06-05:00",
            "max_use": 100,
            "max_use_per_user": 2,
            "details": "Any package for clients",
            "owner": "http://testserver/users/1",
            "applicable_retirements": [],
            "applicable_timeslots": [],
            "applicable_packages": [],
            "applicable_memberships": [],
            "users": []
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
                kwargs={'pk': 1},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
