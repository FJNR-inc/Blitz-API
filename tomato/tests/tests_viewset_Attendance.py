import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.testing_tools import CustomAPITestCase
from blitz_api.factories import UserFactory, AdminFactory
from tomato.models import Attendance
from tomato.factories import AttendanceFactory

User = get_user_model()


class AttendanceTests(CustomAPITestCase):

    ATTRIBUTES = [
        'id',
        'url',
        'key',
        'longitude',
        'latitude',
        'updated_at',
        'created_at',
    ]

    @classmethod
    def setUpClass(cls):
        super(AttendanceTests, cls).setUpClass()

        cls.client = APIClient()

        cls.user = UserFactory()

        cls.admin = AdminFactory()

        cls.attendance = AttendanceFactory()

    def test_create_as_user(self):
        """
        Ensure we can create an attendance as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'key': 'random-key',
        }

        response = self.client.post(
            reverse('attendance-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

    def test_create_as_admin(self):
        """
        Ensure we can create an attendance as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'key': 'random-key',
        }

        response = self.client.post(
            reverse('attendance-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

    def test_create_as_unauthenticated(self):
        """
        Ensure we can't create an attendance without being sign in.
        """

        data = {
            'key': 'random-key',
        }

        response = self.client.post(
            reverse('attendance-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        self.check_attributes(response.json())

        self.assertEqual(
            response.json()['key'],
            'random-key',
        )

    def test_list_as_unauthenticated(self):
        """
        Ensure we can't list attendances as an unauthenticated user.
        """

        response = self.client.get(
            reverse('attendance-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_list_as_user(self):
        """
        Ensure we can't list attendances as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('attendance-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_delete_key(self):
        """
        Ensure we can delete an Attendance based on its key as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        attendance = AttendanceFactory()

        for i in range(9):
            AttendanceFactory()

        response = self.client.post(
            reverse('attendance-delete-key'),
            {
                'key': attendance.key
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertEqual(
            Attendance.objects.filter(key=attendance.key).count(),
            0
        )

    def test_update_key(self):
        """
        Ensure we can update an Attendance based on its key as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        attendance = AttendanceFactory()

        for i in range(9):
            AttendanceFactory()

        response = self.client.post(
            reverse('attendance-update-key'),
            {
                'key': attendance.key
            },
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            Attendance.objects.filter(key=attendance.key).count(),
            1
        )

        self.assertTrue(
            Attendance.objects.get(key=attendance.key).updated_at > attendance.updated_at
        )
