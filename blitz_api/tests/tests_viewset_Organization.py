import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import UserFactory, AdminFactory
from ..models import Organization

User = get_user_model()


class OrganizationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(OrganizationTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.org = Organization.objects.create(name="random_organization")

    def test_create(self):
        """
        Ensure we can create an organization if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake organization",
        }

        response = self.client.post(
            reverse('organization-list'),
            data,
            format='json',
        )

        content = {
            'domains': [],
            'id': 2,
            'name': 'fake organization',
            'url': 'http://testserver/organizations/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a domain with valid organization if user has no
        permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "fake organization",
        }

        response = self.client.post(
            reverse('organization-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list(self):
        """
        Ensure we can list organizations as an unauthenticated user.
        """

        response = self.client.get(
            reverse('organization-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'domains': [],
                'id': 1,
                'name': 'random_organization',
                'url': 'http://testserver/organizations/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
