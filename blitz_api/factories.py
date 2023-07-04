import pytz
from datetime import timedelta, datetime
from django.conf import settings
from django.utils import timezone

from factory.django import DjangoModelFactory
import factory.fuzzy
from django.contrib.auth import get_user_model

from blitz_api.models import (
    Organization,
    AcademicLevel,
    AcademicField,
    MagicLink,
)
from retirement.models import (
    Retreat,
    RetreatDate,
    RetreatType,
    Reservation,
)
from store.models import (
    Order,
    OrderLine,
    OptionProduct,
    OrderLineBaseProduct,
    Coupon,
)
from workplace.models import (
    TimeSlot,
    Reservation as TimeSlotReservation,
    Workplace,
    Period,
)
from faker import Faker

User = get_user_model()
fake = Faker()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('username',)

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    language = User.LANGUAGE_FR
    username = factory.Sequence(lambda n: f'John{n}')
    email = factory.Sequence(lambda n: f'john{n}@blitz.com')
    password = 'Test123!'
    tickets = 1


class AdminFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Sequence('Chuck{0}'.format)
    email = factory.Sequence('chuck{0}@blitz.com'.format)
    password = 'Test123!'
    is_staff = True
    tickets = 1


class OrganizationFactory(DjangoModelFactory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f'Organization {n}')


class AcademicLevelFactory(DjangoModelFactory):
    class Meta:
        model = AcademicLevel

    name = factory.Sequence(lambda n: f'AcademicLevel {n}')


class AcademicFieldFactory(DjangoModelFactory):
    class Meta:
        model = AcademicField

    name = factory.Sequence(lambda n: f'AcademicField {n}')


class MagicLinkFactory(DjangoModelFactory):
    class Meta:
        model = MagicLink

    full_link = 'http://myverylonglink.thatiwantshorten.toamagiclink'
    description = 'This is a factory magic link'


class RetreatTypeFactory(DjangoModelFactory):
    class Meta:
        model = RetreatType

    name = factory.sequence(lambda n: f'Retreat {n}')
    minutes_before_display_link = 1
    number_of_tomatoes = 1


class RetreatFactory(DjangoModelFactory):
    class Meta:
        model = Retreat
        django_get_or_create = ('name',)

    name = factory.sequence(lambda n: f'Retreat {n}')

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
    notification_interval = timedelta(hours=24)
    activity_language = factory.fuzzy.FuzzyChoice(Retreat.ACTIVITY_LANGUAGE)
    price = factory.fuzzy.FuzzyDecimal(0, 1000, 2)
    min_day_refund = factory.fuzzy.FuzzyInteger(0)
    refund_rate = factory.fuzzy.FuzzyInteger(0)
    min_day_exchange = factory.fuzzy.FuzzyInteger(0)
    # users =
    # exclusive_memberships =
    is_active = factory.Faker('boolean', chance_of_getting_true=50)
    email_content = factory.Faker('email')
    accessibility = factory.Faker('boolean', chance_of_getting_true=50)
    has_shared_rooms = factory.Faker('boolean', chance_of_getting_true=50)


class RetreatDateFactory(DjangoModelFactory):

    class Meta:
        model = RetreatDate

    start_time = datetime(2130, 1, 15, 8).astimezone(
        pytz.timezone('America/Montreal'))
    end_time = datetime(2130, 1, 17, 12).astimezone(
        pytz.timezone('America/Montreal'))


class OrderFactory(DjangoModelFactory):

    class Meta:
        model = Order

    transaction_date = timezone.now()
    authorization_id = 1
    settlement_id = 1


class ReservationFactory(DjangoModelFactory):

    class Meta:
        model = Reservation

    is_active = True


class OptionProductFactory(DjangoModelFactory):
    class Meta:
        model = OptionProduct

    name = factory.sequence(lambda n: f'Option Product {n}')
    details = "detail of the option"
    available = True
    price = 50
    max_quantity = 100


class OrderLineFactory(DjangoModelFactory):
    class Meta:
        model = OrderLine

    quantity = 1


class OrderLineBaseProductFactory(DjangoModelFactory):
    class Meta:
        model = OrderLineBaseProduct

    quantity = 1


class CouponFactory(DjangoModelFactory):
    class Meta:
        model = Coupon

    start_time = "2019-01-06T15:11:05-05:00"
    end_time = "2020-01-06T15:11:06-05:00"
    max_use = 100
    max_use_per_user = 2


class WorkplaceFactory(DjangoModelFactory):
    class Meta:
        model = Workplace

    name = factory.Sequence(lambda n: f'Blitz {n}')
    seats = factory.fuzzy.FuzzyInteger(0)
    details = "short_description"
    address_line1 = "123 random street"
    postal_code = "123 456"
    state_province = "Random state"
    country = "Random country"


class PeriodFactory(DjangoModelFactory):
    class Meta:
        model = Period

    name = factory.Sequence(lambda n: f'Period {n}')
    workplace = factory.SubFactory(WorkplaceFactory)
    start_date = LOCAL_TIMEZONE.localize(datetime(2130, 1, 1, 1))
    end_date = LOCAL_TIMEZONE.localize(datetime(2130, 12, 12, 12))
    price = factory.fuzzy.FuzzyDecimal(0, 1000, 2)
    is_active = True


class TimeSlotFactory(DjangoModelFactory):
    class Meta:
        model = TimeSlot

    period = factory.SubFactory(PeriodFactory)
    price = factory.fuzzy.FuzzyDecimal(0, 1000, 2)
    start_time = LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8))
    end_time = LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12))


class TimeSlotReservationFactory(DjangoModelFactory):
    class Meta:
        model = TimeSlotReservation

    user = factory.SubFactory(UserFactory)
    timeslot = factory.SubFactory(TimeSlotFactory)
    is_active = True
