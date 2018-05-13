from rest_framework.test import APITestCase

from ..models import Domain, Organization


class DomainTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(DomainTests, cls).setUpClass()
        cls.org = Organization.objects.create(name="random_university")

    def test_create(self):
        """
        Ensure that we can create a domain with a valid organization.
        """
        domain = Domain.objects.create(
            name="random_domain",
            organization_id=self.org.id
        )

        self.assertEqual(domain.__str__(), "random_domain")

    def test_create_invalid_organization(self):
        """
        Ensure that we can create a domain with an invalid organization.
        """
        domain = Domain.objects.create(
            name="random_domain",
            organization_id=9999
        )

        try:
            domain.organization
            return False
        except Organization.DoesNotExist:
            return True
