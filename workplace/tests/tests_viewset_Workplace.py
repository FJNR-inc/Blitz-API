import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Workplace

User = get_user_model()


class WorkplaceTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkplaceTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.workplace = Workplace.objects.create(
            name="Blitz",
            seats=40,
            details="short_description",
            address_line1="random_address_1",
            postal_code="RAN_DOM",
            city='random_city',
            state_province="Random_State",
            country="Random_Country",
            timezone="America/Montreal",
        )

    def test_create(self):
        """
        Ensure we can create a workplace if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_workplace",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'name': 'random_workplace',
            'timezone': "America/Montreal"
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'details': 'short_description',
            'id': 2,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_workplace',
            'pictures': [],
            'seats': 40,
            'timezone': "America/Montreal",
            'url': 'http://testserver/workplaces/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a workplace if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_workplace",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal"
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_duplicate_name(self):
        """
        Ensure we can't create a workplace with same name.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "Blitz",
            'seats': 40,
            'details': "short_description",
            'address_line1': 'random_address_1',
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'timezone': "America/Montreal"
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {'name': ['This field must be unique.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a workplace when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'details': ['This field is required.'],
            'address_line1': ['This field is required.'],
            'city': ['This field is required.'],
            'country': ['This field is required.'],
            'name': ['This field is required.'],
            'postal_code': ['This field is required.'],
            'seats': ['This field is required.'],
            'state_province': ['This field is required.'],
            'timezone': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create a workplace with invalid fields.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': ("invalid",),
            'seats': "invalid",
            'details': ("invalid",),
            'postal_code': (1,),
            'city': (1,),
            'address_line1': (1,),
            'country': (1,),
            'state_province': (1,),
            'timezone': ("invalid",),
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'details': ['Not a valid string.'],
            'name': ['Not a valid string.'],
            'city': ['Not a valid string.'],
            'address_line1': ['Not a valid string.'],
            'postal_code': ['Not a valid string.'],
            'state_province': ['Not a valid string.'],
            'country': ['Not a valid string.'],
            'seats': ['A valid integer is required.'],
            'timezone': ['Unknown timezone']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a workplace.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "new_workplace",
            'seats': 200,
            'details': "new_short_description",
            'address_line1': 'new_address',
            'city': 'new_city',
            'country': 'Random_Country',
            'postal_code': 'NEW_CIT',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
        }

        response = self.client.put(
            reverse(
                'workplace-detail',
                kwargs={'pk': 1},
            ),
            data,
            format='json',
        )

        content = {
            'details': 'new_short_description',
            'id': 1,
            'longitude': None,
            'latitude': None,
            'address_line1': 'new_address',
            'address_line2': None,
            'city': 'new_city',
            'country': 'Random_Country',
            'postal_code': 'NEW_CIT',
            'state_province': 'Random_State',
            'name': 'new_workplace',
            'pictures': [],
            'seats': 200,
            'timezone': 'America/Montreal',
            'url': 'http://testserver/workplaces/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a workplace.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'workplace-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list workplaces as an unauthenticated user.
        """

        response = self.client.get(
            reverse('workplace-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'details': 'short_description',
                'id': 1,
                'latitude': None,
                'longitude': None,
                'address_line1': 'random_address_1',
                'address_line2': None,
                'city': 'random_city',
                'country': 'Random_Country',
                'postal_code': 'RAN_DOM',
                'state_province': 'Random_State',
                'name': 'Blitz',
                'pictures': [],
                'seats': 40,
                'timezone': 'America/Montreal',
                'url': 'http://testserver/workplaces/1'
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a workplace as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'workplace-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'details': 'short_description',
            'id': 1,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'random_city',
            'country': 'Random_Country',
            'id': 1,
            'longitude': None,
            'latitude': None,
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'name': 'Blitz',
            'pictures': [],
            'seats': 40,
            'timezone': 'America/Montreal',
            'url': 'http://testserver/workplaces/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent_workplace(self):
        """
        Ensure we get not found when asking for a workplace that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'workplace-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
