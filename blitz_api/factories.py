from datetime import timedelta

import factory
import factory.fuzzy
from dateutil.tz import tz
from django.contrib.auth import get_user_model

from blitz_api.models import Organization, AcademicLevel, AcademicField, \
    Address
from retirement.models import Retreat

from faker import Faker

User = get_user_model()
fake = Faker()


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Sequence(lambda n: f'John{n}')
    email = factory.Sequence(lambda n: f'john{n}@blitz.com')
    password = 'Test123!'
    tickets = 1


class AdminFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Sequence('Chuck{0}'.format)
    email = factory.Sequence('chuck{0}@blitz.com'.format)
    password = 'Test123!'
    is_staff = True
    tickets = 1


class OrganizationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f'Organization {n}')


class AcademicLevelFactory(factory.DjangoModelFactory):
    class Meta:
        model = AcademicLevel

    name = factory.Sequence(lambda n: f'AcademicLevel {n}')


class AcademicFieldFactory(factory.DjangoModelFactory):
    class Meta:
        model = AcademicField

    name = factory.Sequence(lambda n: f'AcademicField {n}')


class RetirementFactory(factory.DjangoModelFactory):
    class Meta:
        model = Retreat
        django_get_or_create = ('name',)

    name = factory.sequence(lambda n: f'Retirement {n}')

    place_name = ''
    country = ''
    state_province = factory.Faker('state')
    city = factory.Faker('city')
    address_line1 = 'address'
    address_line2 = factory.Faker('secondary_address')
    postal_code = factory.Faker('postalcode')
    latitude = factory.Faker('latitude')
    longitude = factory.Faker('longitude')
    timezone = factory.Faker('timezone')
    details = factory.Faker('text', max_nb_chars=1000)
    seats = factory.fuzzy.FuzzyInteger(0)
    reserved_seats = 0
    next_user_notified = 0
    notification_interval = timedelta(hours=24)
    activity_language = factory.fuzzy.FuzzyChoice(Retreat.ACTIVITY_LANGUAGE)
    price = factory.fuzzy.FuzzyDecimal(0, 9999, 2)
    start_time = factory.Faker('date_time_between',
                               start_date="+10d", end_date="+30d",
                               tzinfo=tz.tzutc())
    end_time = factory.Faker('date_time_between',
                             start_date="+31d", end_date="+600d",
                             tzinfo=tz.tzutc())
    min_day_refund = factory.fuzzy.FuzzyInteger(0)
    refund_rate = factory.fuzzy.FuzzyInteger(0)
    min_day_exchange = factory.fuzzy.FuzzyInteger(0)
    # users =
    # exclusive_memberships =
    is_active = factory.Faker('boolean', chance_of_getting_true=50)
    email_content = factory.Faker('email')
    accessibility = factory.Faker('boolean', chance_of_getting_true=50)
    has_shared_rooms = factory.Faker('boolean', chance_of_getting_true=50)
