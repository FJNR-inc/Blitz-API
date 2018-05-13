from rest_framework.test import APITestCase

from ..models import AcademicLevel


class AcademicLevelTests(APITestCase):

    def test_create(self):
        """
        Ensure that we can create an academic level.
        """
        lvl = AcademicLevel.objects.create(
            name="random_academic_level",
        )

        self.assertEqual(lvl.__str__(), "random_academic_level")
