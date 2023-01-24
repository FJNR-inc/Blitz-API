from django.core.management.base import BaseCommand

from workplace.models import Reservation
from retirement.tasks import assign_retreat_tomatoes


class Command(BaseCommand):
    help = 'Assign past tomatoes. If tomatoes are already assigned, do ' \
           'nothing. Else add an entry in tomato.Tomato. By default assign ' \
           'all sources. You can specify the source in the parameters.' \
           'List of sources: Retreat, Timeslot'

    def add_arguments(self, parser):
        # Optional arguments
        parser.add_argument('source', type=str, nargs='?', default=None)

    @staticmethod
    def assign_tomatoes_past_retreat():
        """
        Assign all tomatoes for each past date of retreats to user with
        active reservation.
        """
        assign_retreat_tomatoes()

    @staticmethod
    def assign_tomatoes_past_timeslot():
        """
        Assign all tomatoes for each past timeslots to user with
        active reservation.
        """
        for reservation in Reservation.objects.filter(is_active=True):
            reservation.assign_tomatoes(force_assign=True)

    def handle(self, *args, **options):

        source_action = {
            'retreat': self.assign_tomatoes_past_retreat,
            'timeslot': self.assign_tomatoes_past_timeslot,
        }
        source = options['source'].lower()

        if source:
            if source not in source_action:
                self.stdout.write(self.style.ERROR(f'Invalid source {source}'))
            else:
                source_action[source]()
        else:
            for source, action in source_action.items():
                action()
