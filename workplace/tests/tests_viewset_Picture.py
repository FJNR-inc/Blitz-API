import json
import tempfile

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import override_settings

from blitz_api.factories import UserFactory, AdminFactory

from ..models import Workplace, Picture

User = get_user_model()
MEDIA_ROOT = tempfile.mkdtemp()


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
        self.workplace = Workplace.objects.create(
            name="Blitz",
            seats=40,
            details="short_description",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        self.picture = Picture.objects.create(
            name="random_picture",
            picture=self.get_test_image_file().name,
            workplace=self.workplace,
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
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('picture-list'),
            data,
        )

        fname = self.picture_file.name.replace('\\', '/').split("/")[-1]

        content = {
            'id': 2,
            'name': 'random_picture',
            'picture': 'http://testserver/media/workplaces/' + fname,
            'url': 'http://testserver/pictures/2',
            'workplace': 'http://testserver/workplaces/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_without_permission(self):
        """
        Ensure we can't create a picture if user has no permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'name': "random_picture",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('picture-list'),
            data,
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_non_existent_workplace(self):
        """
        Ensure we can't create a picture with a non-existent workplace.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'workplace': reverse('workplace-detail', args=[999]),
            'picture': self.picture_file,
        }

        response = self.client.post(
            reverse('picture-list'),
            data,
        )

        content = {'workplace': ['Invalid hyperlink - Object does not exist.']}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_file(self):
        """
        Ensure we can't create a picture with an invalid file.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'name': "random_picture",
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'picture': "invalid",
        }

        response = self.client.post(
            reverse('picture-list'),
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
            reverse('picture-list'),
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
            'workplace': reverse('workplace-detail', args=[self.workplace.id]),
            'picture': self.picture_file,
        }

        response = self.client.put(
            reverse(
                'picture-detail',
                kwargs={'pk': 1},
            ),
            data,
        )

        content = {
            'id': 1,
            'name': 'new_picture',
            'picture': 'http://testserver/media/workplaces/' + fname,
            'url': 'http://testserver/pictures/1',
            'workplace': 'http://testserver/workplaces/1'
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
                'picture-detail',
                kwargs={'pk': 1},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can list pictures as an unauthenticated user.
        """

        response = self.client.get(
            reverse('picture-list'),
            format='json',
        )

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': 1,
                'name': 'random_picture',
                'picture': 'http://testserver' + self.picture.picture.url,
                'url': 'http://testserver/pictures/1',
                'workplace': 'http://testserver/workplaces/1'
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
                'picture-detail',
                kwargs={'pk': 1},
            ),
        )

        content = {
            'id': 1,
            'name': 'random_picture',
            'picture': 'http://testserver' + self.picture.picture.url,
            'url': 'http://testserver/pictures/1',
            'workplace': 'http://testserver/workplaces/1'
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent_picture(self):
        """
        Ensure we get not found when asking for a picture that doesn't exist.
        """

        response = self.client.get(
            reverse(
                'picture-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
