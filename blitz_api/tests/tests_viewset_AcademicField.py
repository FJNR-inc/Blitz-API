import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from ..factories import UserFactory, AdminFactory
from ..models import AcademicField

User = get_user_model()


class AcademicFieldTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(AcademicFieldTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.field = AcademicField.objects.create(name="random_field")

    def test_create(self):
        """
        Ensure we can create an academic field if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "fake field",
        }

        response = self.client.post(
            reverse('academicfield-list'),
            data,
            format='json',
        )

        content = {
            'id': 2,
            'name': "fake field",
            'url': 'http://testserver/academic_fields/2',
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
            'name': "fake field",
        }

        response = self.client.post(
            reverse('academicfield-list'),
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
        Ensure we can list academic fields as an unauthenticated user.
        """

        response = self.client.get(
            reverse('academicfield-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'name': 'random_field',
                'url': 'http://testserver/academic_fields/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
