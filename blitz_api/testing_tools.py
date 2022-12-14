from rest_framework.test import APITestCase

ORDER_ATTRIBUTES = [
    'id',
    'transaction_date',
    'authorization_id',
    'settlement_id',
    'reference_number',
    'order_lines',
    'total_cost',
    'total_cost_with_taxes',
    'taxes',
    'url',
    'user',
    'is_made_by_admin',
]

ORDERLINE_ATTRIBUTES = [
    'id',
    'url',
    'content_type',
    'coupon_real_value',
    'cost',
    'total_cost',
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

RETREAT_TYPE_ATTRIBUTES = [
    'id',
    'name',
    'url',
    'number_of_tomatoes',
    'is_virtual',
    'is_visible',
    'name_fr',
    'name_en',
    'minutes_before_display_link',
    'description',
    'short_description',
    'duration_description',
    'cancellation_policies',
    'icon',
    'index_ordering',
    'know_more_link',
    'template_id_for_welcome_message',
    'context_for_welcome_message',
]

AUTOMATIC_EMAIL_ATTRIBUTES = [
    'id',
    'url',
    'minutes_delta',
    'time_base',
    'template_id',
    'context',
    'retreat_type',
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
