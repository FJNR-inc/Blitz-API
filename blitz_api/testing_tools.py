from rest_framework.test import APITestCase

ORDER_ATTRIBUTES = [
    'id',
    'transaction_date',
    'authorization_id',
    'settlement_id',
    'reference_number',
    'order_lines',
    'url',
    'user',
]

ORDER_HISTORY_ATTRIBUTES = [
    'id',
    'user',
    'transaction_date',
    'total_cost',
    'total_cost_with_taxes',
    'order_lines',
]

ORDERLINE_ATTRIBUTES = [
    'id',
    'url',
    'content_type',
    'coupon_real_value',
    'cost',
    'coupon',
    'object_id',
    'quantity',
    'metadata',
    'order',
    'name',
    'options'
]

OPTION_ATTRIBUTES = [
    'id',
    'price',
    'quantity',
    'name',
]


class CustomAPITestCase(APITestCase):
    ATTRIBUTES = []

    def check_attributes(self, content, attrs=None):
        if attrs is None:
            attrs = self.ATTRIBUTES

        missing_keys = list(set(attrs) - set(content.keys()))
        extra_keys = list(set(content.keys()) - set(attrs))
        self.assertEqual(
            len(missing_keys),
            0,
            'You miss some attributes: ' + str(missing_keys)
        )
        self.assertEqual(
            len(extra_keys),
            0,
            'You have some extra attributes: ' + str(extra_keys)
        )
