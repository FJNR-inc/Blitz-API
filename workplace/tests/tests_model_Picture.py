import tempfile
import shutil

from rest_framework.test import APITestCase

from django.test import override_settings

from ..models import Workplace, Picture


def get_test_image_file():
    from django.core.files.images import ImageFile
    file = tempfile.NamedTemporaryFile(suffix='.png')
    return ImageFile(file)


MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PictureTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PictureTests, cls).setUpClass()
        cls.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def test_create(self):
        """
        Ensure that we can create a picture.
        """
        picture = Picture.objects.create(
            name="random_picture",
            picture=get_test_image_file().name,
            workplace=self.workplace,
        )

        self.assertEqual(picture.__str__(), "random_picture")

    def test_picture_tag_property(self):
        """
        Ensure that we get proper html code with picture_tag.
        """
        picture = Picture.objects.create(
            name="random_picture",
            picture=get_test_image_file().name,
            workplace=self.workplace,
        )

        self.assertEqual(
            picture.picture_tag(),
            '<img href="' + picture.picture.url +
            '" src="' + picture.picture.url +
            '" height="150" />'
        )
