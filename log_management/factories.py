import factory
from django.utils import timezone

from log_management.models import (
    ActionLog
)
from blitz_api.factories import UserFactory


class ActionLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActionLog

    session_key = factory.Sequence(lambda n: f'session {n}')
    source = 'source'
    action = 'action'

