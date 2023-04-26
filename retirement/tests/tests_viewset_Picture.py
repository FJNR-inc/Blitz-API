import json
import tempfile

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from blitz_api.factories import AdminFactory, UserFactory
from blitz_api.services import remove_translation_fields

from retirement.models import (
    Picture,
    Retreat,
    RetreatType,
)

User = get_user_model()
MEDIA_ROOT = tempfile.mkdtemp()
LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PictureTests(APITestCase):
    def _create_image(self):
        from PIL import Image

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            image = Image.new('RGB', (200, 200), 'white')
            image.save(f, 'PNG')

        return open(f.name, mode='rb')

    @staticmethod
    def get_test_image_file():
        from django.core.files.images import ImageFile
        file = tempfile.NamedTemporaryFile(suffix='.png')
        return ImageFile(file)

    @classmethod
    def setUpClass(cls):
        super(PictureTests, cls).setUpClass()
        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def setUp(self):
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="random_retreat",
            details="This is a description of the retreat.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=3,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            is_active=True,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            display_start_time=timezone.now(),
            type=self.retreatType,
        )
        self.picture = Picture.objects.create(
            name="random_picture",
            picture=self.get_test_image_file().name,
            retreat=self.retreat,
        )
        self.picture_file = self._create_image()

    def tearDown(self):
        self.picture_file.close()

    def test_create(self):
        """
        Ensure we can create a picture if user has permission.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retreat:picture-list'),
            data,
        )

        fname = self.picture_file.name.replace('\\', '/').split("/")[-1]

        content = {
            'name': 'random_picture',
            'picture': 'http://testserver/media/retreats/' + fname,
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.retreat.id)
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
        Ensure we can't create a picture if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_picture",
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retreat:picture-list'),
            data,
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_non_existent_workplace(self):
        """
        Ensure we can't create a picture with a non-existent retreat.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'retreat': reverse('retreat:retreat-detail', args=[999]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retreat:picture-list'),
            data,
        )

        content = {
            'retreat': ['Invalid hyperlink - Object does not exist.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_file(self):
        """
        Ensure we can't create a picture with an invalid file.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]),
            'picture': "invalid",
        }

        response = self.client.post(
            reverse('retreat:picture-list'),
            data,
        )

        content = {
            'picture': [
                'The submitted data was not a file. Check the encoding type '
                'on the form.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_field(self):
        """
        Ensure we can't create a picture when required fields are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('retreat:picture-list'),
            data,
            format='json',
        )

        content = {
            'name': ['This field is required.'],
            'picture': ['No file was submitted.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        """
        Ensure we can update a picture.
        """
        self.client.force_authenticate(user=self.admin)

        fname = self.picture_file.name.replace('\\', '/').split("/")[-1]

        data = {
            'name': "new_picture",
            'retreat': reverse(
                'retreat:retreat-detail', args=[self.retreat.id]),
            'picture': self.picture_file,
        }

        response = self.client.put(
            reverse(
                'retreat:picture-detail',
                kwargs={'pk': self.picture.id},
            ),
            data,
        )

        content = {
            'id': self.picture.id,
            'name': 'new_picture',
            'name_en': 'new_picture',
            'name_fr': None,
            'picture': 'http://testserver/media/retreats/' + fname,
            'url': 'http://testserver/retreat/pictures/' +
                   str(self.picture.id),
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.retreat.id)
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete a picture.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'retreat:picture-detail',
                kwargs={'pk': self.picture.id},
            ), )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list pictures as an unauthenticated user.
        """

        response = self.client.get(
            reverse('retreat:picture-list'),
            format='json',
        )

        content = {
            'count':
            1,
            'next':
            None,
            'previous':
            None,
            'results': [{
                'id': self.picture.id,
                'name': 'random_picture',
                'picture': 'http://testserver' + self.picture.picture.url,
                'url': 'http://testserver/retreat/pictures/' +
                       str(self.picture.id),
                'retreat': 'http://testserver/retreat/retreats/' +
                           str(self.retreat.id)
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can read a picture as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'retreat:picture-detail',
                kwargs={'pk': self.picture.id},
            ), )

        content = {
            'id': self.picture.id,
            'name': 'random_picture',
            'picture': 'http://testserver' + self.picture.picture.url,
            'url': 'http://testserver/retreat/pictures/' +
                   str(self.picture.id),
            'retreat': 'http://testserver/retreat/retreats/' +
                       str(self.retreat.id)
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent_picture(self):
        """
        Ensure we get not found when asking for a picture that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'retreat:picture-detail',
                kwargs={'pk': 999},
            ), )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
