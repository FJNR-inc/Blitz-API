import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory, AdminFactory
from location.models import Address, Country, StateProvince
from location.serializers import AddressBasicSerializer

from ..models import Workplace

User = get_user_model()


class WorkplaceTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkplaceTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()
        cls.random_country = Country.objects.create(
            name="Random_Country",
            iso_code="RC",
        )
        cls.random_state_province = StateProvince.objects.create(
            name="Random_State",
            iso_code="RS",
            country=cls.random_country,
        )
        cls.address = Address.objects.create(
            address_line1='random_address_1',
            postal_code='RAN_DOM',
            city='random_city',
            state_province=cls.random_state_province,
            country=cls.random_country,
        )

    def setUp(self):
        self.workplace = Workplace.objects.create(
            name="Blitz",
            seats=40,
            details="short_description",
            location=self.address,
        )

    def test_create(self):
        """
        Ensure we can create a workplace if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        # Serialize our address object and set FK instead of nested repr.
        location = AddressBasicSerializer(self.address).data
        location['country'] = self.address.country.pk
        location['state_province'] = self.address.state_province.pk

        data = {
            'name': "random_workplace",
            'seats': 40,
            'details': "short_description",
            'location': location,
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'details': 'short_description',
            'location': {
                'address_line1': 'random_address_1',
                'address_line2': '',
                'city': 'random_city',
                'country': {'iso_code': 'RC', 'name': 'Random_Country'},
                'id': 1,
                'postal_code': 'RAN_DOM',
                'state_province': {'iso_code': 'RS', 'name': 'Random_State'}
            },
            'name': 'random_workplace',
            'seats': 40,
            'url': 'http://testserver/workplaces/2'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a workplace if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        # Serialize our address object and set FK instead of nested repr.
        location = AddressBasicSerializer(self.address).data
        location['country'] = self.address.country.pk
        location['state_province'] = self.address.state_province.pk

        data = {
            'name': "random_workplace",
            'seats': 40,
            'details': "short_description",
            'location': location,
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

        # Serialize our address object and set FK instead of nested repr.
        location = AddressBasicSerializer(self.address).data
        location['country'] = self.address.country.pk
        location['state_province'] = self.address.state_province.pk

        data = {
            'name': "Blitz",
            'seats': 40,
            'details': "short_description",
            'location': location,
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {'name': ['This field must be unique.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_non_existent_location(self):
        """
        Ensure we can't create a workplace with a non-existent location.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "unique_name",
            'seats': 40,
            'details': "short_description",
            'location': {
                'address_line1': 'invalid_address_line',
                'address_line2': '',
                'city': 'random_city',
                'country': 'RC',
                'id': 1,
                'postal_code': 'RAN_DOM',
                'state_province': 'RS',
            },
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {'location': ['This address does not exist.']}

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
            'location': ['This field is required.'],
            'name': ['This field is required.'],
            'seats': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_location_content(self):
        """
        Ensure we can't create a workplace when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "unique_name",
            'seats': 40,
            'details': "short_description",
            'location': {},
        }

        response = self.client.post(
            reverse('workplace-list'),
            data,
            format='json',
        )

        content = {
            'location': {
                'address_line1': ['This field is required.'],
                'city': ['This field is required.'],
                'country': ['This field is required.'],
                'postal_code': ['This field is required.'],
                'state_province': ['This field is required.']
            }
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a workplace.
        """
        self.client.force_authenticate(user=self.admin)

        # Serialize our address object and set FK instead of nested repr.
        address = Address.objects.create(
            address_line1='new_address',
            postal_code='NEW_CIT',
            city='new_city',
            state_province=self.random_state_province,
            country=self.random_country,
        )
        location = AddressBasicSerializer(address).data
        location['country'] = address.country.pk
        location['state_province'] = address.state_province.pk

        data = {
            'name': "new_workplace",
            'seats': 200,
            'details': "new_short_description",
            'location': location,
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
            'location': {
                'address_line1': 'new_address',
                'address_line2': '',
                'city': 'new_city',
                'country': {'iso_code': 'RC', 'name': 'Random_Country'},
                'id': 2,
                'postal_code': 'NEW_CIT',
                'state_province': {'iso_code': 'RS', 'name': 'Random_State'}},
            'name': 'new_workplace',
            'seats': 200,
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
                'location': {
                    'address_line1': 'random_address_1',
                    'address_line2': '',
                    'city': 'random_city',
                    'country': {
                        'iso_code': 'RC',
                        'name': 'Random_Country'
                    },
                    'id': 1,
                    'postal_code': 'RAN_DOM',
                    'state_province': {
                        'iso_code': 'RS',
                        'name': 'Random_State'
                    }
                },
                'name': 'Blitz',
                'seats': 40,
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
            'location': {
                'address_line1': 'random_address_1',
                'address_line2': '',
                'city': 'random_city',
                'country': {
                    'iso_code': 'RC',
                    'name': 'Random_Country'
                },
                'id': 1,
                'postal_code': 'RAN_DOM',
                'state_province': {
                    'iso_code': 'RS',
                    'name': 'Random_State'
                }
            },
            'name': 'Blitz',
            'seats': 40,
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
