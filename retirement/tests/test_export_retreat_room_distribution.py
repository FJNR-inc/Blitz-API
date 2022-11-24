from unittest import mock
from django.test import TestCase
from datetime import datetime

from django.contrib.contenttypes.models import ContentType

import pytz
from django.conf import settings
from retirement.models import (
    RetreatType,
    RetreatDate,
    Retreat
)
from retirement.exports import generate_retreat_participation
from blitz_api.models import ExportMedia
from blitz_api.factories import AdminFactory

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class TestExportAnonymousChronoDataTask(TestCase):

    def setUp(self):
        self.admin = AdminFactory()
        self.retreat_type = ContentType.objects.get_for_model(Retreat)
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()

    @mock.patch('retirement.models.Retreat.get_retreat_room_distribution')
    @mock.patch('blitz_api.models.ExportMedia.send_confirmation_email')
    def test_export_retreat_room_distribution(
            self,
            mock_email,
            mock_room_distribution
    ):
        """
        """
        mock_email.return_value = None
        mock_room_distribution.return_value = [
            {
                'first_name': 'Joshua',
                'last_name': 'Berry',
                'email': '16@test.ca',
                'room_option': 'single',
                'gender_preference': 'NA',
                'share_with': 'NA',
                'room_number': 1,
                'placed': True,
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Hancock',
                'email': '17@test.ca',
                'room_option': 'single',
                'gender_preference': 'NA',
                'share_with': 'NA',
                'room_number': 2,
                'placed': True,
            },
            {
                'first_name': 'Lisa',
                'last_name': 'Wright',
                'email': '1@test.ca',
                'room_option': 'shared',
                'gender_preference': 'mixte',
                'share_with': '14@test.ca',
                'room_number': 3,
                'placed': True,
            },
            {
                'first_name': 'Matthew',
                'last_name': 'Ross',
                'email': '14@test.ca',
                'room_option': 'shared',
                'gender_preference': 'woman',
                'share_with': '1@test.ca',
                'room_number': 3,
                'placed': True,
            },
            {
                'first_name': 'Robert',
                'last_name': 'Haas',
                'email': '2@test.ca',
                'room_option': 'shared',
                'gender_preference': 'man',
                'share_with': '11@test.ca',
                'room_number': 4,
                'placed': True,
            },
            {
                'first_name': 'Justin',
                'last_name': 'Martin',
                'email': '11@test.ca',
                'room_option': 'shared',
                'gender_preference': 'woman',
                'share_with': '2@test.ca',
                'room_number': 4,
                'placed': True,
            }
        ]
        generate_retreat_participation(self.admin.id, self.retreat.id)
        self.assertEqual(
            ExportMedia.objects.all().count(),
            1)
        export = ExportMedia.objects.all().first()
        self.assertEqual(
            export.type,
            ExportMedia.EXPORT_RETREAT_PARTICIPATION)
