import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import UserFactory, AdminFactory
from ..models import Organization, Domain

User = get_user_model()


class DomainTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(DomainTests, cls).setUpClass()
        cls.org = Organization.objects.create(name="random_university")
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.domain = Domain.objects.create(
            name="random.domain",
            organization_id=cls.org.id,
        )

    def test_create(self):
        """
        Ensure we can create a domain with valid organization if user has
        permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake.domain",
            'example': "email@fake.domain",
            'organization': reverse('organization-detail', args=[self.org.id]),
        }

        response = self.client.post(
            reverse('domain-list'),
            data,
            format='json',
        )

        content = {
            'id': 2,
            'example': "email@fake.domain",
            'name': 'fake.domain',
            'organization': 'http://testserver/organizations/1',
            'url': 'http://testserver/domains/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid_organization(self):
        """
        Ensure we can't create a domain with invalid organization if user has
        permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake.domain",
            'organization': reverse('organization-detail', args=[999]),
        }

        response = self.client.post(
            reverse('domain-list'),
            data,
            format='json',
        )

        content = {
            'organization': ['Invalid hyperlink - Object does not exist.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_without_permission(self):
        """
        Ensure we can't create a domain with valid organization if user has no
        permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "fake.domain",
            'organization': reverse('organization-detail', args=[self.org.id]),
        }

        response = self.client.post(
            reverse('domain-list'),
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
        Ensure we can list domains as an unauthenticated user.
        """

        response = self.client.get(
            reverse('domain-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'example': None,
                'name': 'random.domain',
                'organization': 'http://testserver/organizations/1',
                'url': 'http://testserver/domains/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
