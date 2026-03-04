import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import (
    UserFactory, 
    AdminFactory, 
    OrganizationFactory,
    AffiliationFactory,
)
from ..models import Organization, Affiliation
from ..services import remove_translation_fields

User = get_user_model()


class AffiliationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(AffiliationTests, cls).setUpClass()
        cls.org = Organization.objects.create(name="random_university")
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.affiliation = Affiliation.objects.create(
            name="random.affiliation",
            organization_id=cls.org.id,
        )

    def test_create(self):
        """
        Ensure we can create an affiliation with valid organization if user has
        permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake.affiliation",
            'organization': reverse('organization-detail', args=[self.org.id]),
        }

        response = self.client.post(
            reverse('affiliation-list'),
            data,
            format='json',
        )

        content = {
            'name': 'fake.affiliation',
            'organization': f'http://testserver/organizations/{str(self.org.id)}/',
        }

        response_data = remove_translation_fields(json.loads(response.content))
        del response_data['url']
        del response_data['id']

        self.assertEqual(
            response_data,
            content
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid_organization(self):
        """
        Ensure we can't create an affiliation with invalid organization if user has
        permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake.affiliation",
            'organization': reverse('organization-detail', args=[999]),
        }

        response = self.client.post(
            reverse('affiliation-list'),
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
        Ensure we can't create an affiliation with valid organization if user has no
        permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "fake.affiliation",
            'organization': reverse('organization-detail', args=[self.org.id]),
        }

        response = self.client.post(
            reverse('affiliation-list'),
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
        Ensure we can list affiliations as an unauthenticated user.
        """

        response = self.client.get(
            reverse('affiliation-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.affiliation.id,
                'name': 'random.affiliation',
                'organization': f'http://testserver/organizations/{str(self.org.id)}/',
                'url': f'http://testserver/affiliations/{str(self.affiliation.id)}/'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


    def test_list_filtered_by_organization(self):
        """
        Ensure we can get a list of affiliations filtered by organizatio nas an unauthenticated user.
        """

        organization = OrganizationFactory()
        affiliation = AffiliationFactory(organization=organization)
        
        affiliation_non_filtered = AffiliationFactory()

        response = self.client.get(
            reverse('affiliation-list') + f'?organization={organization.id}',
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': affiliation.id,
                'name': affiliation.name,
                'organization': f'http://testserver/organizations/{str(organization.id)}/',
                'url': f'http://testserver/affiliations/{str(affiliation.id)}/'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
