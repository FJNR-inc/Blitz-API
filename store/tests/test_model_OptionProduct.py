from datetime import timedelta

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory, RetreatFactory
from blitz_api.models import AcademicLevel
from retirement.models import Retreat

from ..models import Order, OptionProduct, Package


class OptionProductTests(APITestCase):

    def setUp(self):
        self.user = UserFactory()
        self.retreat = RetreatFactory()
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
