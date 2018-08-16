import factory
from django.contrib.auth import get_user_model

User = get_user_model()


class UserFactory(factory.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    username = factory.Sequence('John{0}'.format)
    email = factory.Sequence('john{0}@blitz.com'.format)
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
