from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import User


class UserTests(APITestCase):

    def test_generate_tomato_field_matrix(self):
        """
        test that matrix generation works and cells that need to be filled
        are.
        """
        user = UserFactory()
        matrix = user.generate_tomato_field_matrix()

        # Matrix size is 5x5
        self.assertEqual(len(matrix), 5)
        for row in matrix:
            self.assertEqual(len(row), 5)

        # Common ThV bench is located on 4,0
        matrix[4][0] = user.TOMATO_MATRIX_CELLS_BENCH

        cells = []
        for row in matrix:
            cells += row

        # We shouldn't have more than 1 animal
        self.assertEqual(
            sum(f in user.TOMATO_MATRIX_CELLS_ANIMAL for f in cells),
            1,
        )

        # We shouldn't have more than 2 decoration
        self.assertEqual(
            sum(f in user.TOMATO_MATRIX_CELLS_DECORATION for f in cells),
            2,
        )

        # We shouldn't have more than 5 default cell
        self.assertEqual(
            cells.count(user.TOMATO_MATRIX_CELLS_DEFAULT),
            5,
        )

        # We shouldn't have more than 16 default field
        self.assertEqual(
            cells.count(user.TOMATO_MATRIX_CELLS_DEFAULT_FIELD),
            16,
        )

        # We shouldn't have more than 1 ThV bench
        self.assertEqual(
            cells.count(user.TOMATO_MATRIX_CELLS_BENCH),
            1,
        )
