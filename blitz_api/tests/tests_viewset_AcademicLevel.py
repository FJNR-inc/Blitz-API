import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import UserFactory, AdminFactory
from ..models import AcademicLevel

User = get_user_model()


class AcademicLevelTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(AcademicLevelTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.lvl = AcademicLevel.objects.create(name="random_level")

    def test_create(self):
        """
        Ensure we can create an academic level if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake level",
        }

        response = self.client.post(
            reverse('academiclevel-list'),
            data,
            format='json',
        )

        content = {
            'id': 2,
            'name': "fake level",
            'url': 'http://testserver/academic_levels/2',
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
            'name': "fake level",
        }

        response = self.client.post(
            reverse('academiclevel-list'),
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
        Ensure we can list academic levels as an unauthenticated user.
        """

        response = self.client.get(
            reverse('academiclevel-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'name': 'random_level',
                'url': 'http://testserver/academic_levels/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
