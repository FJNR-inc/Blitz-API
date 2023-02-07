from django.test import SimpleTestCase

from utils.tomato_field import TomatoFieldManager


class TomatoFieldManagerTests(SimpleTestCase):

    def test_generate_tomato_field_matrix(self):
        """
        test that matrix generation works and cells that need to be filled
        are.
        """
        matrix = TomatoFieldManager.generate_tomato_field_matrix()

        # Matrix size is 5x5
        self.assertEqual(len(matrix), 5)
        for row in matrix:
            self.assertEqual(len(row), 5)

        # Common ThV bench is located on 4,0
        matrix[4][0] = TomatoFieldManager.TOMATO_MATRIX_CELLS_BENCH

        cells = []
        for row in matrix:
            cells += row
        self.assertEqual(
            sum(f in TomatoFieldManager.TOMATO_MATRIX_CELLS_ANIMAL
                for f in cells),
            TomatoFieldManager.TOMATO_MATRIX_NUMBER_OF_ANIMAL,
        )

        self.assertEqual(
            sum(f in TomatoFieldManager.TOMATO_MATRIX_CELLS_DECORATION
                for f in cells),
            TomatoFieldManager.TOMATO_MATRIX_NUMBER_OF_DECORATION,
        )

        # We shouldn't have more than 5 default cell
        self.assertEqual(
            cells.count(TomatoFieldManager.TOMATO_MATRIX_CELLS_DEFAULT),
            5,
        )

        # We shouldn't have more than 16 default field
        self.assertEqual(
            cells.count(TomatoFieldManager.TOMATO_MATRIX_CELLS_DEFAULT_FIELD),
            16,
        )

        # We shouldn't have more than 1 ThV bench
        self.assertEqual(
            cells.count(TomatoFieldManager.TOMATO_MATRIX_CELLS_BENCH),
            1,
        )
