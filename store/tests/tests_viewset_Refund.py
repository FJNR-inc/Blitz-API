import json

from datetime import timedelta

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Order, OrderLine, Package, Refund

User = get_user_model()


class RefundTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(RefundTests, cls).setUpClass()
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
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.order_admin = Order.objects.create(
            user=cls.admin,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        cls.order_line = OrderLine.objects.create(
            order=cls.order,
            quantity=1,
            content_type=cls.package_type,
            object_id=1,
        )
        cls.order_line_admin = OrderLine.objects.create(
            order=cls.order_admin,
            quantity=99,
            content_type=cls.package_type,
            object_id=1,
        )
        cls.refund = Refund.objects.create(
            orderline=cls.order_line,
            refund_date=timezone.now(),
            amount=10.00,
            details="Refund details",
        )
        cls.refund_admin = Refund.objects.create(
            orderline=cls.order_line_admin,
            refund_date=timezone.now(),
            amount=10.00,
            details="Admin refund details",
        )

    def test_list(self):
        """
        Ensure we can't list refunds as an unauthenticated user.
        """
        response = self.client.get(
            reverse('refund-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_owner(self):
        """
        Ensure we can list owned refunds as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('refund-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'orderline': 'http://testserver/order_lines/1',
                'id': 1,
                'details': "Refund details",
                'amount': '10.00',
                'refund_date': response_data['results'][0]['refund_date'],
                'refund_id': None,
                'url': 'http://testserver/refunds/1'
            }]
        }

        self.assertEqual(response_data, content)

    def test_list_admin(self):
        """
        Ensure we can list all refunds as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('refund-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        response_data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'orderline': 'http://testserver/order_lines/1',
                'id': 1,
                'details': "Refund details",
                'amount': '10.00',
                'refund_date': response_data['results'][0]['refund_date'],
                'refund_id': None,
                'url': 'http://testserver/refunds/1'
            }, {
                'orderline': 'http://testserver/order_lines/2',
                'id': 2,
                'details': "Admin refund details",
                'amount': '10.00',
                'refund_date': response_data['results'][1]['refund_date'],
                'refund_id': None,
                'url': 'http://testserver/refunds/2'
            }]
        }

        self.assertEqual(response_data, content)

    def test_read_unauthenticated(self):
        """
        Ensure we can't read a refund as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'refund-detail',
                kwargs={'pk': self.refund.id},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_owner(self):
        """
        Ensure we can read a refund owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'refund-detail',
                kwargs={'pk': self.refund.id},
            ),
        )

        response_data = json.loads(response.content)

        content = {
            'orderline': 'http://testserver/order_lines/1',
            'id': 1,
            'details': "Refund details",
            'amount': '10.00',
            'refund_date': response_data['refund_date'],
            'refund_id': None,
            'url': 'http://testserver/refunds/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_owner_not_owned(self):
        """
        Ensure we can't read a refund not owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'refund-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure we can read any refund as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'refund-detail',
                kwargs={'pk': self.refund.id},
            ),
        )

        response_data = json.loads(response.content)

        content = {
            'orderline': 'http://testserver/order_lines/1',
            'id': 1,
            'details': "Refund details",
            'amount': '10.00',
            'refund_date': response_data['refund_date'],
            'refund_id': None,
            'url': 'http://testserver/refunds/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for a refund that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'refund-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
