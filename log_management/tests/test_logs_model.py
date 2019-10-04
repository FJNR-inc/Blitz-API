import json

from django.test import TestCase

from log_management.models import Log


class LogsTests(TestCase):
    def test_create_error(self):
        additional_data = {
            'title': "Place exclusive pour 24h",
            'default_from': 'from@email',
            'user_email': 'user.email',
            'merge_data': 'merge_data',
            'template': 'reserved_place'
        }
        new_log = Log.error(
            source='SENDING_BLUE_TEMPLATE',
            message='err',
            additional_data=json.dumps(additional_data)
        )

        self.assertEqual(new_log.source, 'SENDING_BLUE_TEMPLATE')
