from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from ..models import Affiliation, Organization


class AffiliationTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(AffiliationTests, cls).setUpClass()
        cls.org = Organization.objects.create(name="random_university")

    def test_create(self):
        """
        Ensure that we can create an affiliation with a valid organization.
        """
        affiliation = Affiliation.objects.create(
            name="random_affiliation",
            organization_id=self.org.id
        )

        self.assertEqual(affiliation.__str__(), "random_affiliation")
