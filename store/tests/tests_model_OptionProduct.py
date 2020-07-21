import pytz
from django.utils import timezone
from django.conf import settings
from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase
from blitz_api.factories import UserFactory, RetreatFactory
from retirement.models import Retreat, RetreatDate, RetreatType
from store.models import Order, OptionProduct, Package

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class OptionProductTests(APITestCase):

    def setUp(self):
        self.user = UserFactory()
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
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()
        self.retreat_content_types = ContentType.objects.get_for_model(Retreat)
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

        self.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=400,
            reservations=100,
        )

        self.options_1: OptionProduct = OptionProduct.objects.create(
            name="options_1",
            details="options_1",
            available=True,
            price=50.00,
            max_quantity=10,
        )
        self.options_1.available_on_products.add(self.package)
        self.options_1.save()

        self.retreat_option = RetreatFactory()
        self.retreat_option.is_active = True
        self.retreat_option.available_on_products.add(self.package)
        self.retreat_option.save()

    def test_create_for_retreat_object(self):
        option_product = OptionProduct.objects.create(
            name="Vegan",
            details="Vegan details",
            available=True,
            price=50,
            max_quantity=10
        )

        option_product.available_on_products.add(self.retreat)
        option_product.save()

        self.retreat.refresh_from_db()

        self.assertIn(option_product, list(self.retreat.options))

    def test_create_for_retreat_type(self):
        option_product = OptionProduct.objects.create(
            name="Vegan",
            details="Vegan details",
            available=True,
            price=50,
            max_quantity=10
        )

        option_product.available_on_product_types.add(
            self.retreat_content_types)
        option_product.save()

        self.retreat.refresh_from_db()

        self.assertIn(option_product, list(self.retreat.options))

    def test_options_package(self):
        self.assertIn(self.options_1, list(self.package.options))
        self.assertIn(self.retreat_option, list(self.package.options))
