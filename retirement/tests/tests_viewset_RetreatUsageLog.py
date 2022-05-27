import json
from datetime import (
    datetime,
    timedelta,
)
from django.utils import timezone
import pytz
import responses
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from blitz_api.factories import (
    AdminFactory,
    UserFactory,
)
from blitz_api.testing_tools import CustomAPITestCase
from store.models import (
    Order,
    OrderLine,
)
from retirement.models import (
    Retreat,
    RetreatType,
    RetreatDate,
    Reservation,
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatUsageLogTests(CustomAPITestCase):
    ATTRIBUTES = [
        'id',
        'url',
        'reservation',
        'datetime',
    ]

    def setUp(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.admin = AdminFactory()

        self.retreat_content_type = ContentType.objects.get_for_model(Retreat)

        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega retreat",
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
            activity_language='FR',
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

        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.retreat_content_type,
            object_id=self.retreat.id,
            cost=self.retreat.price,
        )
        self.reservation = Reservation.objects.create(
            user=self.user,
            retreat=self.retreat,
            order_line=self.order_line,
            is_active=True,
        )

    def test_create_retreat_usage_log(self):
        """
        Ensure we can create a retreat usage log if user has permission.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'reservation': reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            )
        }

        response = self.client.post(
            reverse('retreat:retreatusagelog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        content = json.loads(response.content)

        self.check_attributes(content)

    def test_create_retreat_usage_log_on_somebody_else_reservation(self):
        """
        Ensure we can't create a retreat usage log if reservation is not our.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'reservation': reverse(
                'retreat:reservation-detail',
                kwargs={'pk': self.reservation.id},
            )
        }

        response = self.client.post(
            reverse('retreat:retreatusagelog-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        content = json.loads(response.content)

        self.assertEquals(
            content,
            {
                'reservation': [
                   "You need to own the reservation to log a usage."
                ]
            }
        )
