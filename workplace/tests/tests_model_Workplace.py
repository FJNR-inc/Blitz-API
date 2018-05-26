from rest_framework.test import APITestCase

from location.models import Address, Country, StateProvince

from ..models import Workplace


class WorkplaceTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(WorkplaceTests, cls).setUpClass()
        cls.random_country = Country.objects.create(
            name="Random Country",
            iso_code="RC",
        )
        cls.random_state_province = StateProvince.objects.create(
            name="Random State",
            iso_code="RS",
            country=cls.random_country,
        )
        cls.address = Address.objects.create(
            address_line1='random address 1',
            postal_code='RAN DOM',
            city='random city',
            state_province=cls.random_state_province,
            country=cls.random_country,
        )

    def test_create(self):
        """
        Ensure that we can create a workplace.
        """
        workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            location=self.address,
        )

        self.assertEqual(workplace.__str__(), "random_workplace")
