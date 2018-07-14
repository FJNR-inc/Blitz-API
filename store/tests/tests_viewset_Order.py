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


class OrderTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrderTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        cls.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        cls.membership.academic_levels.set([cls.academic_level])
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            transaction_id=1,
        )
        cls.order_admin = Order.objects.create(
            user=cls.admin,
            transaction_date=timezone.now(),
            transaction_id=1,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=1,
        )

    def test_create(self):
        """
        Ensure we can create an order if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': reverse('user-detail', args=[self.user.id]),
            'transaction_date': timezone.now(),
            'transaction_id': 1,
            'order_lines': [{
                'content_type': 'membership',
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'id': 3,
            'order_lines': [{
                'content_type': 'membership',
                'id': 2,
                'object_id': 1,
                'order': 'http://testserver/orders/3',
                'quantity': 1,
                'url': 'http://testserver/order_lines/2'
            }],
            'url': 'http://testserver/orders/3',
            'user': 'http://testserver/users/1',
            'transaction_date': data['transaction_date'].astimezone()
                                                        .isoformat(),
            'transaction_id': '1',
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create an order if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'user': reverse('user-detail', args=[self.user.id]),
            'transaction_date': timezone.now(),
            'transaction_id': 1,
        }

        response = self.client.post(
            reverse('order-list'),
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
        Ensure we can't create an order when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'transaction_date': ['This field is required.'],
            'transaction_id': ['This field is required.'],
            'user': ['This field is required.'],
            'order_lines': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create an order when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': None,
            'transaction_date': None,
            'transaction_id': None,
            'order_lines': None,
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'transaction_date': ['This field may not be null.'],
            'transaction_id': ['This field may not be null.'],
            'user': ['This field may not be null.'],
            'order_lines': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create an order when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': "invalid",
            'transaction_date': (1,),
            'transaction_id': "invalid",
            'order_lines': (1,),
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'transaction_date': [
                'Datetime has wrong format. Use one of these formats '
                'instead: YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].'
            ],
            'user': ['Invalid hyperlink - No URL match.'],
            'order_lines': [{
                'non_field_errors': [
                    'Invalid data. Expected a dictionary, but got int.'
                ]
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update an order.
        An empty 'order_lines' list will be ignored.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': reverse('user-detail', args=[self.user.id]),
            'transaction_date': timezone.now(),
            'transaction_id': 2,
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 99,
                'url': 'http://testserver/order_lines/1'
            }],
        }

        response = self.client.put(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'id': 1,
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1',
            'transaction_date': data['transaction_date'].astimezone()
                                                        .isoformat(),
            'transaction_id': '2',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 99,
                'url': 'http://testserver/order_lines/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete an order.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can't list orders as an unauthenticated user.
        """
        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_owner(self):
        """
        Ensure we can list owned orders as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'transaction_id': '1',
                'order_lines': [{
                    'content_type': 'package',
                    'id': 1,
                    'object_id': 1,
                    'order': 'http://testserver/orders/1',
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/1'
                }],
                'url': 'http://testserver/orders/1',
                'user': 'http://testserver/users/1'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_admin(self):
        """
        Ensure we can list all orders as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'transaction_date': data['results'][0]['transaction_date'],
                'transaction_id': '1',
                'order_lines': [{
                    'content_type': 'package',
                    'id': 1,
                    'object_id': 1,
                    'order': 'http://testserver/orders/1',
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/1'
                }],
                'url': 'http://testserver/orders/1',
                'user': 'http://testserver/users/1'
            }, {
                'id': 2,
                'transaction_date': data['results'][1]['transaction_date'],
                'transaction_id': '1',
                'order_lines': [],
                'url': 'http://testserver/orders/2',
                'user': 'http://testserver/users/2'
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can't read an order as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_owner(self):
        """
        Ensure we can read an order owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'transaction_id': '1',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }],
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_owner_not_owned(self):
        """
        Ensure we can't read an order not owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure we can read any order as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 1},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': 1,
            'transaction_date': data['transaction_date'],
            'transaction_id': '1',
            'order_lines': [{
                'content_type': 'package',
                'id': 1,
                'object_id': 1,
                'order': 'http://testserver/orders/1',
                'quantity': 1,
                'url': 'http://testserver/order_lines/1'
            }],
            'url': 'http://testserver/orders/1',
            'user': 'http://testserver/users/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for an order that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
