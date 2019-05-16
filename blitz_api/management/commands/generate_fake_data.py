from blitz_api.factories import UserFactory, OrganizationFactory, \
    RetirementFactory
from django.core.management.base import BaseCommand

from blitz_api.models import User, Organization, Address
from retirement.models import Retirement


class Command(BaseCommand):
    help = 'Generate users with UserFactory'

    def add_arguments(self, parser):
        parser.add_argument('nb_data', type=int)

    def handle(self, *args, **options):

        nb_user = options['nb_data']

        nb_user_in_db = User.objects.all().count()
        UserFactory.create_batch(nb_user)

        nb_user_in_db = User.objects.all().count()
        self.stdout.write(self.style.SUCCESS(
            f"{nb_user_in_db} "
            f"user(s) in database"))

        for x in range(nb_user_in_db, nb_user_in_db + nb_user):
            OrganizationFactory(__sequence=x)

        nb_organization_in_db = Organization.objects.all().count()
        self.stdout.write(self.style.SUCCESS(
            f"{nb_organization_in_db} "
            f"Orga(s) in database"))

        RetirementFactory.create_batch(nb_user)
        nb_organization_in_db = Retirement.objects.all().count()
        self.stdout.write(self.style.SUCCESS(
            f"{nb_organization_in_db} "
            f"Retirement(s) in database"))
