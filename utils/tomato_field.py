import random
import copy


class TomatoFieldManager:
    """
    Class providing functions and constants to handle Tomato field for users
    """
    TOMATO_MATRIX_NUMBER_OF_ANIMAL = 1
    TOMATO_MATRIX_NUMBER_OF_DECORATION = 2

    # Name of cells match image file name
    TOMATO_MATRIX_CELLS_ANIMAL = [
        'grass_pig_2',
        'grass_cow',
        'grass_horse',
        'grass_goat',
        'grass_dog',
        'grass_chicken',
        'grass_pig',
        'grass_sheep_2',
        'grass_sheep',
    ]
    TOMATO_MATRIX_CELLS_DECORATION = [
        'grass_well',
        'grass_straw',
        'grass_wood_2',
        'grass_wood',
        'grass_lawn',
        'grass_tree_2',
        'grass_tree',
    ]
    TOMATO_MATRIX_CELLS_DEFAULT = 'grass'
    TOMATO_MATRIX_CELLS_DEFAULT_FIELD = 'field_0'
    TOMATO_MATRIX_CELLS_BENCH = 'grass_thv'

    TOMATO_MATRIX_CELLS = [
        *TOMATO_MATRIX_CELLS_DEFAULT,
        *TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
        *TOMATO_MATRIX_CELLS_BENCH,
        *TOMATO_MATRIX_CELLS_DECORATION,
        *TOMATO_MATRIX_CELLS_ANIMAL,
    ]

    TOMATO_MATRIX_BASE = [
        [
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT,
        ],
        [
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
        ],
        [
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
        ],
        [
            TOMATO_MATRIX_CELLS_DEFAULT,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
        ],
        [
            TOMATO_MATRIX_CELLS_BENCH,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
            TOMATO_MATRIX_CELLS_DEFAULT_FIELD,
        ],
    ]

    TOMATO_MATRIX_RANDOM_CELLS = [
        (0, 0),
        (0, 1),
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 0),
        (2, 0),
        (3, 0),
    ]

    @classmethod
    def generate_tomato_field_matrix(cls):
        """
        Generate a matrix with personalised cells
        return the generated matrix as a list of list
        """
        matrix = copy.deepcopy(cls.TOMATO_MATRIX_BASE)

        # Decide which cell should be personalised
        total_number_of_personalisation = \
            cls.TOMATO_MATRIX_NUMBER_OF_DECORATION + \
            cls.TOMATO_MATRIX_NUMBER_OF_ANIMAL

        cell_to_personalise = random.sample(
            cls.TOMATO_MATRIX_RANDOM_CELLS,
            total_number_of_personalisation,
        )

        cell_count = 0
        # Personalisation of animals
        random_animals = random.sample(
            cls.TOMATO_MATRIX_CELLS_ANIMAL,
            cls.TOMATO_MATRIX_NUMBER_OF_ANIMAL,
        )
        for animal in random_animals:
            cell = cell_to_personalise[cell_count]
            matrix[cell[0]][cell[1]] = animal
            cell_count += 1

        # Personalisation of decorations
        random_decorations = random.sample(
            cls.TOMATO_MATRIX_CELLS_DECORATION,
            cls.TOMATO_MATRIX_NUMBER_OF_DECORATION,
        )
        for decoration in random_decorations:
            cell = cell_to_personalise[cell_count]
            matrix[cell[0]][cell[1]] = decoration
            cell_count += 1

        return matrix
