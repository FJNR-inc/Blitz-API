import json

from datetime import timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from blitz_api.factories import UserFactory, AdminFactory

from blitz_api.models import AcademicLevel
from ..models import Package, Order, OrderLine, Membership

User = get_user_model()


class PackageTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PackageTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            price=400,
            reservations=100,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            transaction_id=1,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=1,
        )
        cls.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            price=50,
            duration=timedelta(days=365),
            academic_level=cls.academic_level,
        )

    def test_create(self):
        """
        Ensure we can create a package if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "basic_package",
            'details': "10 reservations package",
            'price': 50,
            'reservations': 10,
            'exclusive_memberships': [
                reverse('membership-detail', args=[self.membership.id]),
            ],
        }

        response = self.client.post(
            reverse('package-list'),
            data,
            format='json',
        )

        content = {
            'details': '10 reservations package',
            'exclusive_memberships': ['http://testserver/memberships/1'],
            'id': 2,
            'name': 'basic_package',
            'order_lines': [],
            'price': '50.00',
            'reservations': 10,
            'url': 'http://testserver/packages/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a package if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "basic_package",
            'details': "10 reservations package",
            'price': 50,
            'reservations': 10,
        }

        response = self.client.post(
            reverse('package-list'),
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
        Ensure we can't create a package when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('package-list'),
            data,
            format='json',
        )

        content = {
            'name': ['This field is required.'],
            'price': ['This field is required.'],
            'reservations': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create a package when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': None,
            'details': None,
            'price': None,
            'reservations': None,
            'exclusive_memberships': None,
        }

        response = self.client.post(
            reverse('package-list'),
            data,
            format='json',
        )

        content = {
            'exclusive_memberships': ['This field may not be null.'],
            'name': ['This field may not be null.'],
            'price': ['This field may not be null.'],
            'reservations': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a package when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': (1,),
            'details': (1,),
            'price': "",
            'reservations': "",
            'exclusive_memberships': (1,),
        }

        response = self.client.post(
            reverse('package-list'),
            data,
            format='json',
        )

        content = {
            'details': ['Not a valid string.'],
            'exclusive_memberships': [
                'Incorrect type. Expected URL string, received int.'
            ],
            'name': ['Not a valid string.'],
            'price': ['A valid number is required.'],
            'reservations': ['A valid integer is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a package.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "extreme_package_updated",
            'details': "999 reservations package",
            'price': 1,
            'reservations': 999,
        }

        response = self.client.put(
            reverse(
                'package-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'details': '999 reservations package',
            'exclusive_memberships': [],
            'id': 1,
            'name': 'extreme_package_updated',
            'order_lines': ['http://testserver/order_lines/1'],
            'price': '1.00',
            'reservations': 999,
            'url': 'http://testserver/packages/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_partial(self):
        """
        Ensure we can partially update a package.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'details': "New very cool details",
            'price': 99,
        }

        response = self.client.patch(
            reverse(
                'package-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'details': 'New very cool details',
            'exclusive_memberships': [],
            'id': 1,
            'name': 'extreme_package',
            'order_lines': ['http://testserver/order_lines/1'],
            'price': '99.00',
            'reservations': 100,
            'url': 'http://testserver/packages/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a package.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'package-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list packages as an unauthenticated user.
        """
        response = self.client.get(
            reverse('package-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'details': '100 reservations package',
                'exclusive_memberships': [],
                'id': 1,
                'name': 'extreme_package',
                'price': '400.00',
                'reservations': 100,
                'url': 'http://testserver/packages/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a package as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'package-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'details': '100 reservations package',
            'exclusive_memberships': [],
            'id': 1,
            'name': 'extreme_package',
            'price': '400.00',
            'reservations': 100,
            'url': 'http://testserver/packages/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_admin(self):
        """
        Ensure we can read a package's order lines as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'package-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'details': '100 reservations package',
            'exclusive_memberships': [],
            'id': 1,
            'name': 'extreme_package',
            'order_lines': ['http://testserver/order_lines/1'],
            'price': '400.00',
            'reservations': 100,
            'url': 'http://testserver/packages/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a package that doesn't
        exist.
        """

        response = self.client.get(
            reverse(
                'package-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
