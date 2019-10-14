import csv
import datetime
import random
import string

from io import StringIO
from colorama import Fore
from django.core.management import call_command
from tqdm import tqdm

from blitz_api.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Import members "from new_members.csv" file'

    def add_arguments(self, parser):

        # Optional arguments
        parser.add_argument(
            '--notify',
            action='store_true',
            dest='notify',
            help='Notify new user with his credentials',
        )

    def handle(self, *args, **options):

        notify = options['notify']

        with open('new_members.csv') as csv_file:
            csv_reader = csv.DictReader(csv_file)

            with tqdm(list(csv_reader), unit=' users', desc='Import users ',
                      bar_format="{l_bar}%s{bar}%s{r_bar}" %
                                 (Fore.GREEN, Fore.RESET)
                      ) as pbar:

                nb_user_created = 0
                nb_user_updated = 0

                for user_data in pbar:

                    try:

                        out = StringIO()

                        nb_users = User.objects.all().count()

                        letters_and_digits = \
                            string.ascii_letters + string.digits
                        password = ''.join(
                            random.choice(letters_and_digits)
                            for i in range(10))

                        birthdate = datetime.datetime.strptime(
                            user_data["birthdate"], '%d/%m/%Y')
                        birthdate = birthdate.strftime('%Y-%m-%d')

                        if notify:

                            call_command(
                                'create_member',
                                f'--first_name={user_data["first_name"]}',
                                f'--last_name={user_data["last_name"]}',
                                f'--birthdate={birthdate}',
                                f'--gender={user_data["first_name"]}',
                                f'--university={user_data["university"]}',
                                f'--academic_level='
                                f'{user_data["academic_level"]}',
                                f'--academic_field='
                                f'{user_data["academic_field"]}',
                                f'--email={user_data["email"]}',
                                f'--password={password}',
                                f'--membership={user_data["membership"]}',
                                '--notify',
                                stdout=out
                            )
                        else:

                            call_command(
                                'create_member',
                                f'--first_name={user_data["first_name"]}',
                                f'--last_name={user_data["last_name"]}',
                                f'--birthdate={birthdate}',
                                f'--gender={user_data["first_name"]}',
                                f'--university={user_data["university"]}',
                                f'--academic_level='
                                f'{user_data["academic_level"]}',
                                f'--academic_field='
                                f'{user_data["academic_field"]}',
                                f'--email={user_data["email"]}',
                                f'--password={password}',
                                # No security on password
                                f'--membership={user_data["membership"]}',
                                stdout=out)

                        if User.objects.all().count() - nb_users == 0:
                            nb_user_updated += 1
                        else:
                            nb_user_created += 1

                    except CommandError as e:
                        self.stdout.write(
                            self.style.ERROR(f'{e}'))

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created {nb_user_created} users'))

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully updated {nb_user_updated} users'))
