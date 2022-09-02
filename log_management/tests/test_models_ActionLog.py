from django.test import TestCase

from log_management.factories import ActionLogFactory
from blitz_api.factories import (
    UserFactory,
)

from log_management.models import ActionLog


class ActionLogModelTests(TestCase):

    def test_anonymize_data(self):
        """
        test the anonymization of data, make sure the uuid is different for all users and always the same for
        same user. Same for session key.
        """
        user_1 = UserFactory()
        user_2 = UserFactory()
        user_1_session_key = "user_1_key"
        user_2_session_key = "user_2_key"

        ActionLogFactory(user=user_1, session_key=user_1_session_key)
        ActionLogFactory(user=user_1, session_key=user_1_session_key)
        ActionLogFactory(user=user_1, session_key=user_1_session_key)

        ActionLogFactory(user=user_2, session_key=user_2_session_key)
        ActionLogFactory(user=user_2, session_key=user_2_session_key)

        anonymous_data = ActionLog.anonymize_data()

        self.assertEqual(
            len(anonymous_data),
            5
        )
        user_1_anonymized_id = anonymous_data[1]["user"]
        user_2_anonymized_id = anonymous_data[4]["user"]

        user_1_anonymized_key = anonymous_data[1]["session_key"]
        user_2_anonymized_key = anonymous_data[4]["session_key"]

        self.assertNotEqual(
            user_1_anonymized_id,
            user_2_anonymized_id
        )
        self.assertNotEqual(
            user_1_anonymized_key,
            user_2_anonymized_key
        )

        self.assertNotEqual(
            user_1_anonymized_id,
            user_1.id
        )
        self.assertNotEqual(
            user_2_anonymized_id,
            user_2.id
        )
        self.assertNotEqual(
            user_1_anonymized_key,
            user_1_session_key
        )
        self.assertNotEqual(
            user_2_anonymized_key,
            user_2_session_key
        )

        user_1_data = []
        user_2_data = []
        for action in anonymous_data:
            if action["user"] == user_1_anonymized_id and action["session_key"] == user_1_anonymized_key:
                user_1_data.append(action)
            elif action["user"] == user_2_anonymized_id and action["session_key"] == user_2_anonymized_key:
                user_2_data.append(action)
        self.assertEqual(
            len(user_1_data),
            3
        )
        self.assertEqual(
            len(user_2_data),
            2
        )
