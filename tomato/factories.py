from faker import Faker
import factory.fuzzy
from factory.django import DjangoModelFactory

from django.contrib.auth import get_user_model

from blitz_api.factories import UserFactory
from tomato.models import (
    Attendance,
    Tomato,
)

User = get_user_model()
fake = Faker()


class AttendanceFactory(DjangoModelFactory):
    class Meta:
        model = Attendance

    key = factory.Sequence(lambda n: f'Key-{n}')


class TomatoFactory(DjangoModelFactory):
    class Meta:
        model = Tomato

    user = factory.SubFactory(UserFactory)
    number_of_tomato = 2
