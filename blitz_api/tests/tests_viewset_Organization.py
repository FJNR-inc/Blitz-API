import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import UserFactory, AdminFactory
from ..models import Organization
from ..services import remove_translation_fields

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
            'name': 'fake organization',
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['url']
        del response_data['id']

        self.assertEqual(
            response_data,
            content
        )

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
                'id': self.org.id,
                'name': 'random_organization',
                'url': 'http://testserver/organizations/' + str(self.org.id)
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_search_name(self):
        """
        Ensure we can list organizations as an unauthenticated user and search
        by name
        """
        Organization.objects.create(name="test 1")
        Organization.objects.create(name="test 2")
        Organization.objects.create(name="unknown 1")
        Organization.objects.create(name="unknown 2")

        response = self.client.get(
            reverse('organization-list'),
            {
                'search': 'test'
            },
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        content = json.loads(response.content)

        self.assertEqual(len(content['results']), 2)
