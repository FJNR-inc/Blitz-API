import json
import pytz
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from blitz_api.factories import (
    AdminFactory,
    UserFactory,
)
from blitz_api.testing_tools import (
    CustomAPITestCase,
    RETREAT_TYPE_ATTRIBUTES
)


from retirement.models import (
    RetreatType,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)
MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class RetreatTypeTests(CustomAPITestCase):
    """
    Note: 2 retreat types are already created by migration they are
    named Physical and Virtual
    """
    ATTRIBUTES = RETREAT_TYPE_ATTRIBUTES

    def _create_image(self):
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')

        return open(f.name, mode='rb')

    @classmethod
    def setUpClass(cls):
        super(RetreatTypeTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreatType = RetreatType.objects.create(
            name="example 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,)

        self.retreatType2 = RetreatType.objects.create(
            name="different type",
            minutes_before_display_link=10,
            number_of_tomatoes=4,)

        self.retreatType3 = RetreatType.objects.create(
            name="invisible",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
            is_visible=False,)
        self.picture_file = self._create_image()

    def tearDown(self):
        self.picture_file.close()

    def test_list_admin(self):
        """
        Test that admin can list all RT
        """
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            reverse('retreat:retreattype-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(content['results']),
            RetreatType.objects.all().count()
        )
        self.check_attributes(content['results'][0])

    def test_list_user(self):
        """
        Test that user can list only visible RT
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('retreat:retreattype-list'),
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(content['results']),
            RetreatType.objects.filter(is_visible=True).count()
        )
        self.check_attributes(content['results'][0])

    def test_create_by_admin(self):
        """
        Test that admin can create a RT
        """
        self.client.force_authenticate(user=self.admin)
        data = {
            'name': 'My new RT',
            'number_of_tomatoes': 1,
            'is_virtual': True,
            'is_visible': True,
            'minutes_before_display_link': 1,
            'description': 'Desc of new RT',
            'short_description': 'Like a trouser but with shorter legs',
            'duration_description': 'time of a period',
            'cancellation_policies': 'Inspecteur lapolice',
            'index_ordering': 1,
            'context_for_welcome_message': 'Hello',
            'icon': self.picture_file,
        }
        response = self.client.post(
            reverse('retreat:retreattype-list'),
            data,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RetreatType.objects.get(name='My new RT'))

    def test_create_by_user(self):
        """
        Test that user can't create a RT
        """
        self.client.force_authenticate(user=self.user)
        data = {
            'name': 'WTV',
        }
        response = self.client.post(
            reverse('retreat:retreattype-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_by_admin(self):
        """
        Ensure admin can update a retreat type.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "no more invisible",
            'is_visible': True,
        }

        response = self.client.patch(
            reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType3.id]
            ),
            data,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        now_visible = RetreatType.objects.get(pk=self.retreatType3.id)
        self.assertEqual(now_visible.name, "no more invisible")
        self.assertTrue(now_visible.is_visible)

    def test_update_by_user(self):
        """
        Ensure user can't update a retreat type.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "no more invisible",
            'is_visible': True,
        }

        response = self.client.put(
            reverse(
                'retreat:retreattype-detail',
                args=[self.retreatType3.id]
            ),
            data,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_search_name_retreattype(self):
        """
        Ensure we can search a Retreat type by name
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('retreat:retreattype-list'),
            {
                'search': 'exam'
            },
            format='json',
        )

        content = json.loads(response.content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['results']), 1)
        self.assertEqual(content['results'][0]['name'], self.retreatType.name)
