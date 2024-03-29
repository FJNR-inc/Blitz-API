import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory
from blitz_api.services import remove_translation_fields

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
            'timezone': "America/Montreal",
            'volunteers': [f"http://testserver/users/{self.user.id}"],
            'is_accessible': False,
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        response_content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)

        content = {
            'details': 'short_description',
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'random_city',
            'country': 'Random_Country',
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'latitude': None,
            'longitude': None,
            'name': 'random_workplace',
            'geolocation_link': None,
            'pictures': [],
            'seats': 40,
            'timezone': "America/Montreal",
            'place_name': '',
            'volunteers': [
                f'http://testserver/users/{self.user.id}'
            ],
            'is_accessible': False,
        }

        del response_content['id']
        del response_content['url']

        self.assertEqual(
            remove_translation_fields(response_content),
            content
        )

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
            'place_name': (1,),
            'volunteers': (1,),
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
            'timezone': ['Unknown timezone'],
            'place_name': ['Not a valid string.'],
            'volunteers': [
                'Incorrect type. Expected URL string, received int.'
            ],
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
            'geolocation_link': 'https://goo.gl/maps/YmWaRRvShFQ2MFMs6',
            'postal_code': 'NEW_CIT',
            'state_province': 'Random_State',
            'timezone': "America/Montreal",
            'is_accessible': False,
        }

        response = self.client.put(
            reverse(
                'workplace-detail',
                kwargs={'pk': self.workplace.id},
            ),
            data,
            format='json',
        )

        content = {
            'details': 'new_short_description',
            'id': self.workplace.id,
            'longitude': None,
            'latitude': None,
            'address_line1': 'new_address',
            'address_line2': None,
            'city': 'new_city',
            'country': 'Random_Country',
            'postal_code': 'NEW_CIT',
            'state_province': 'Random_State',
            'name': 'new_workplace',
            'geolocation_link': 'https://goo.gl/maps/YmWaRRvShFQ2MFMs6',
            'pictures': [],
            'seats': 200,
            'timezone': 'America/Montreal',
            'place_name': '',
            'volunteers': [],
            'url': f'http://testserver/workplaces/{self.workplace.id}',
            'is_accessible': False,
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)),
            content
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a workplace.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'workplace-detail',
                kwargs={'pk': self.workplace.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list_unauthenticated(self):
        """
        Ensure we can list workplaces as an unauthenticated user. Only seeing
        accessible worplaces
        """

        Workplace.objects.create(
            name="Inaccessible",
            seats=40,
            details="short_description",
            address_line1="random_address_1",
            postal_code="RAN_DOM",
            city='random_city',
            state_province="Random_State",
            country="Random_Country",
            timezone="America/Montreal",
            is_accessible=False,
        )

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
                'id': self.workplace.id,
                'latitude': None,
                'longitude': None,
                'address_line1': 'random_address_1',
                'address_line2': None,
                'city': 'random_city',
                'country': 'Random_Country',
                'postal_code': 'RAN_DOM',
                'state_province': 'Random_State',
                'name': 'Blitz',
                'geolocation_link': None,
                'pictures': [],
                'seats': 40,
                'timezone': 'America/Montreal',
                'place_name': '',
                'volunteers': [],
                'url': f'http://testserver/workplaces/{self.workplace.id}',
                'is_accessible': True,
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_admin(self):
        """
        Ensure we can list workplaces as an admin user.
        """
        self.client.force_authenticate(user=self.admin)
        Workplace.objects.create(
            name="Inaccessible",
            seats=40,
            details="short_description",
            address_line1="random_address_1",
            postal_code="RAN_DOM",
            city='random_city',
            state_province="Random_State",
            country="Random_Country",
            timezone="America/Montreal",
            is_accessible=False,
        )

        response = self.client.get(
            reverse('workplace-list'),
            format='json',
        )

        self.assertEqual(json.loads(response.content)['count'], 2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_user(self):
        """
        Ensure we can list workplaces as user, only seeing accessible
        """

        Workplace.objects.create(
            name="Inaccessible",
            seats=40,
            details="short_description",
            address_line1="random_address_1",
            postal_code="RAN_DOM",
            city='random_city',
            state_province="Random_State",
            country="Random_Country",
            timezone="America/Montreal",
            is_accessible=False,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('workplace-list'),
            format='json',
        )
        content = json.loads(response.content)
        self.assertEqual(content['count'], 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a workplace as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'workplace-detail',
                kwargs={'pk': self.workplace.id},
            ),
        )

        content = {
            'details': 'short_description',
            'id': self.workplace.id,
            'address_line1': 'random_address_1',
            'address_line2': None,
            'city': 'random_city',
            'country': 'Random_Country',
            'longitude': None,
            'latitude': None,
            'postal_code': 'RAN_DOM',
            'state_province': 'Random_State',
            'name': 'Blitz',
            'geolocation_link': None,
            'pictures': [],
            'seats': 40,
            'place_name': '',
            'timezone': 'America/Montreal',
            'volunteers': [],
            'url': f'http://testserver/workplaces/{self.workplace.id}',
            'is_accessible': True,
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
