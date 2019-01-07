from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory

from ..models import Package, Coupon


class CouponTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(CouponTests, cls).setUpClass()
        cls.package_type = ContentType.objects.get_for_model(Package)
        cls.user = UserFactory()
        cls.coupon = Coupon.objects.create(
            value=13,
            code="ASD1234E",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for fjeanneau clients",
            owner=cls.user,
        )
        cls.coupon.applicable_product_types.add(cls.package_type)
        cls.coupon.save()

    def test_create(self):
        """
        Ensure that we can create a coupon.
        """
        coupon = Coupon.objects.create(
            value=13,
            code="12345678",
            start_time="2019-01-06T15:11:05-05:00",
            end_time="2020-01-06T15:11:06-05:00",
            max_use=100,
            max_use_per_user=2,
            details="Any package for fjeanneau clients",
            owner=self.user,
        )

        self.assertEqual(str(coupon), "12345678")
