import datetime
from datetime import timedelta

from blitz_api.exceptions import MailServiceError
from blitz_api.models import AcademicField, AcademicLevel, Organization, User
from blitz_api.services import notify_user_of_new_account
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from store.models import Membership


class Command(BaseCommand):
    help = 'Create a new active user with a membership ' \
           'and send him a welcome email'

    def add_arguments(self, parser):
        parser.add_argument('--first_name', nargs='+', required=True, type=str)
        parser.add_argument('--last_name', nargs='+', required=True, type=str)
        parser.add_argument('--birthdate', required=True, type=str)
        parser.add_argument('--gender', required=True, type=str)
        parser.add_argument('--university', required=True, type=int)
        parser.add_argument('--academic_level', required=True, type=int)
        parser.add_argument('--academic_field', required=True, type=int)
        parser.add_argument('--email', required=True, type=str)
        parser.add_argument('--password', required=True, type=str)
        parser.add_argument('--membership', required=True, type=int)

        # Optional arguments
        parser.add_argument(
            '--notify',
            action='store_true',
            dest='notify',
            help='Notify new user with his credentials',
        )

        # Optional arguments
        parser.add_argument(
            '--check_email',
            action='store_true',
            dest='check_email',
            help='Check email new user',
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            try:
                validate_email(options['email'])
            except ValidationError:
                raise CommandError(
                    'Email "%s" is not a valid email' % options['email'])

            user = User.objects.filter(email__iexact=options['email'])

            if len(user) == 0:
                if options['check_email']:
                    raise CommandError(
                        'A user already exists with the email {0}'.format(
                            options['email'],
                        )
                    )
                try:
                    user = User.create_user(
                        first_name=' '.join(options['first_name']),
                        last_name=' '.join(options['last_name']),
                        birthdate=options['birthdate'],
                        gender=options['gender'],
                        email=options['email'],
                        password=options['password'],
                        university=options['university'],
                        academic_level=options['academic_level'],
                        academic_field=options['academic_field']
                    )

                    if options['notify'] is True:
                        try:
                            notify_user_of_new_account(options['email'],
                                                       options['password'])
                        except MailServiceError:
                            raise CommandError(
                                'Email service is down, "--notify" '
                                'option is not available')

                except Exception as err:
                    raise CommandError(f'{err}')
            else:
                user = user[0]
            try:
                user.offer_free_membership(options['membership'])

            except Exception as err:
                raise CommandError(f'{err}')

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully created user "%s"' % options['email']))
