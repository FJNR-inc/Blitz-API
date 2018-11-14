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

    def handle(self, *args, **options):
        with transaction.atomic():
            try:
                validate_email(options['email'])
            except ValidationError:
                raise CommandError(
                    'Email "%s" is not a valid email' % options['email'])

            if User.objects.filter(email__iexact=options['email']):
                raise CommandError(
                    'A user already exists with the email {0}'.format(
                        options['email'],
                    )
                )

            user = User.objects.create(
                first_name=' '.join(options['first_name']),
                last_name=' '.join(options['last_name']),
                birthdate=options['birthdate'],
                gender=options['gender'],
                username=options['email'],
                email=options['email'],
                is_active=True,
                tickets=1,
            )
            user.set_password(options['password'])

            try:
                university = Organization.objects.get(pk=options['university'])
                user.university = university
                user.save()
            except Organization.DoesNotExist:
                raise CommandError(
                    'Organization "%s" does not exist' % options['university'])

            try:
                academic_field = AcademicField.objects.get(
                    pk=options['academic_field'])
                user.academic_field = academic_field
                user.save()
            except AcademicField.DoesNotExist:
                raise CommandError('AcademicField "%s" does not exist' %
                                   options['academic_field'])

            try:
                academic_level = AcademicLevel.objects.get(
                    pk=options['academic_level'])
                user.academic_level = academic_level
                user.save()
            except AcademicLevel.DoesNotExist:
                raise CommandError('AcademicLevel "%s" does not exist' %
                                   options['academic_level'])

            try:
                membership = Membership.objects.get(pk=options['membership'])
                user.membership = membership
                end_date = datetime.datetime.now() + membership.duration
                user.membership_end = end_date
                user.save()
            except Membership.DoesNotExist:
                raise CommandError(
                    'Membership "%s" does not exist' % options['membership'])

            if options['notify'] is True:
                try:
                    notify_user_of_new_account(options['email'],
                                               options['password'])
                except MailServiceError:
                    raise CommandError('Email service is down, "--notify" '
                                       'option is not available')

            self.stdout.write(
                self.style.SUCCESS(
                    'Successfully created user "%s"' % options['email']))
