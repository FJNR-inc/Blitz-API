from rest_framework.test import APITestCase

from ..models import Workplace


class WorkplaceTests(APITestCase):

    def test_create(self):
        """
        Ensure that we can create a workplace.
        """
        workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )

        self.assertEqual(workplace.__str__(), "random_workplace")
