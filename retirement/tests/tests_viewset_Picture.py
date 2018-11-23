import json
import tempfile
from datetime import datetime

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from blitz_api.factories import AdminFactory, UserFactory
from blitz_api.services import remove_translation_fields

from ..models import Picture, Retirement

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
        self.retirement = Retirement.objects.create(
            name="random_retirement",
            details="This is a description of the retirement.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=100,
            is_active=True,
        )
        self.picture = Picture.objects.create(
            name="random_picture",
            picture=self.get_test_image_file().name,
            retirement=self.retirement,
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retirement:picture-list'),
            data,
        )

        fname = self.picture_file.name.replace('\\', '/').split("/")[-1]

        content = {
            'id': 2,
            'name': 'random_picture',
            'picture': 'http://testserver/media/retirements/' + fname,
            'url': 'http://testserver/retirement/pictures/2',
            'retirement': 'http://testserver/retirement/retirements/1'
        }

        self.assertEqual(
            remove_translation_fields(json.loads(response.content)), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a picture if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_picture",
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retirement:picture-list'),
            data,
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_non_existent_workplace(self):
        """
        Ensure we can't create a picture with a non-existent retirement.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'retirement': reverse('retirement:retirement-detail', args=[999]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('retirement:picture-list'),
            data,
        )

        content = {
            'retirement': ['Invalid hyperlink - Object does not exist.']
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]),
            'picture': "invalid",
        }

        response = self.client.post(
            reverse('retirement:picture-list'),
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
            reverse('retirement:picture-list'),
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
            'retirement': reverse(
                'retirement:retirement-detail', args=[self.retirement.id]),
            'picture': self.picture_file,
        }

        response = self.client.put(
            reverse(
                'retirement:picture-detail',
                kwargs={'pk': 1},
            ),
            data,
        )

        content = {
            'id': 1,
            'name': 'new_picture',
            'name_en': 'new_picture',
            'name_fr': None,
            'picture': 'http://testserver/media/retirements/' + fname,
            'url': 'http://testserver/retirement/pictures/1',
            'retirement': 'http://testserver/retirement/retirements/1'
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
                'retirement:picture-detail',
                kwargs={'pk': 1},
            ), )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list pictures as an unauthenticated user.
        """

        response = self.client.get(
            reverse('retirement:picture-list'),
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
                'id':
                1,
                'name':
                'random_picture',
                'picture':
                'http://testserver' + self.picture.picture.url,
                'url':
                'http://testserver/retirement/pictures/1',
                'retirement':
                'http://testserver/retirement/retirements/1'
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
                'retirement:picture-detail',
                kwargs={'pk': 1},
            ), )

        content = {
            'id': 1,
            'name': 'random_picture',
            'picture': 'http://testserver' + self.picture.picture.url,
            'url': 'http://testserver/retirement/pictures/1',
            'retirement': 'http://testserver/retirement/retirements/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent_picture(self):
        """
        Ensure we get not found when asking for a picture that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'retirement:picture-detail',
                kwargs={'pk': 999},
            ), )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
