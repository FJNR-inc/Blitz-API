from rest_framework.test import APITestCase

from ..models import AcademicField


class AcademicFieldTests(APITestCase):

    def test_create(self):
        """
        Ensure that we can create an academic level.
        """
        field = AcademicField.objects.create(
            name="random_academic_field",
        )

        self.assertEqual(field.__str__(), "random_academic_field")
