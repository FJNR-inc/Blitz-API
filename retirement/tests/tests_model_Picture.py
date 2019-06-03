import shutil
import tempfile
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APITestCase

from ..models import Picture, Retreat


def get_test_image_file():
    from django.core.files.images import ImageFile
    file = tempfile.NamedTemporaryFile(suffix='.png')
    return ImageFile(file)


MEDIA_ROOT = tempfile.mkdtemp()
LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class PictureTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        super(PictureTests, cls).setUpClass()
        cls.retreat = Retreat.objects.create(
            name="random_retreat",
            details="This is a description of the retreat.",
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
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True
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
            retreat=self.retreat,
        )

        self.assertEqual(picture.__str__(), "random_picture")

    def test_picture_tag_property(self):
        """
        Ensure that we get proper html code with picture_tag.
        """
        picture = Picture.objects.create(
            name="random_picture",
            picture=get_test_image_file().name,
            retreat=self.retreat,
        )

        self.assertEqual(
            picture.picture_tag(), '<img href="' + picture.picture.url +
            '" src="' + picture.picture.url + '" height="150" />')
