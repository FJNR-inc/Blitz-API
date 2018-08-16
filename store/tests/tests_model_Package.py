from datetime import timedelta

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import AcademicLevel

from ..models import Package, Order, OrderLine


class PackageTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(PackageTests, cls).setUpClass()
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.user = UserFactory()
        cls.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

    def test_create(self):
        """
        Ensure that we can create a package.
        """
        package = Package.objects.create(
            name="basic_package",
            details="10 reservations package",
            available=True,
            price=50,
            reservations=10,
        )

        self.assertEqual(str(package), "basic_package")

    def test_package_order_lines(self):
        """
        Ensure that we can get order lines for a specific package.
        """
        package = Package.objects.create(
            name="basic_package",
            details="10 reservations package",
            available=True,
            price=50,
            reservations=10,
        )
        OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=1,
        )

        self.assertEqual(
            str(package.order_lines.all()[0]),
            "basic_package, qt:1"
        )
