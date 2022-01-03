from datetime import timedelta

import factory
from factory.django import DjangoModelFactory
import factory.fuzzy
from dateutil.tz import tz
from django.contrib.auth import get_user_model

from tomato.models import Attendance

from faker import Faker

User = get_user_model()
fake = Faker()


class AttendanceFactory(DjangoModelFactory):
    class Meta:
        model = Attendance

    key = factory.Sequence(lambda n: f'Key-{n}')
