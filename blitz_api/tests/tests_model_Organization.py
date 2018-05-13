from rest_framework.test import APITestCase

from ..models import Organization


class OrganizationTests(APITestCase):

    def test_create(self):
        """
        Ensure that we can create a organization.
        """
        org = Organization.objects.create(
            name="random_organization",
        )

        self.assertEqual(org.__str__(), "random_organization")
