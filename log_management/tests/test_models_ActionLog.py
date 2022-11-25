from django.test import TestCase

from log_management.factories import ActionLogFactory
from blitz_api.factories import (
    UserFactory,
)

from log_management.models import ActionLog


class ActionLogModelTests(TestCase):

    def test_anonymize_data(self):
        """
        test the anonymization of data, make sure the uuid is different for
        all users and always the same for same user. Same for session key.
        """
        user_1 = UserFactory()
        user_2 = UserFactory()
        user_3_session_key = "user_3_key"
        user_4_session_key = "user_4_key"

        ActionLogFactory(user=user_1)
        ActionLogFactory(user=user_1)
        ActionLogFactory(user=user_1)

        ActionLogFactory(user=user_2)
        ActionLogFactory(user=user_2)

        ActionLogFactory(session_key=user_3_session_key)
        ActionLogFactory(session_key=user_3_session_key)

        ActionLogFactory(session_key=user_4_session_key)
        ActionLogFactory(session_key=user_4_session_key)

        anonymous_data = ActionLog.anonymize_data()

        self.assertEqual(
            len(anonymous_data),
            9
        )
        user_1_anonymized_id = anonymous_data[1]["user"]
        user_2_anonymized_id = anonymous_data[4]["user"]

        user_3_anonymized_key = anonymous_data[6]["user"]
        user_4_anonymized_key = anonymous_data[8]["user"]

        self.assertNotEqual(
            user_1_anonymized_id,
            user_2_anonymized_id
        )
        self.assertNotEqual(
            user_3_anonymized_key,
            user_4_anonymized_key
        )

        self.assertNotEqual(
            user_1_anonymized_id,
            user_1.id
        )
        self.assertNotEqual(
            user_2_anonymized_id,
            user_2.id
        )
        user_1_data = []
        user_2_data = []
        user_3_data = []
        user_4_data = []
        for action in anonymous_data:
            if action["user"] == user_1_anonymized_id:
                user_1_data.append(action)
            elif action["user"] == user_2_anonymized_id:
                user_2_data.append(action)
            elif action["user"] == user_3_anonymized_key:
                user_3_data.append(action)
            elif action["user"] == user_4_anonymized_key:
                user_4_data.append(action)
        self.assertEqual(
            len(user_1_data),
            3
        )
        self.assertEqual(
            len(user_2_data),
            2
        )
        self.assertEqual(
            len(user_3_data),
            2
        )
        self.assertEqual(
            len(user_4_data),
            2
        )
