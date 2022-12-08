import binascii
import os
import json
import traceback
from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import mail_admins
from django.core.mail import send_mail as django_send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from rest_framework import serializers as rest_framework_serializers

from blitz_api.services import send_mail as send_templated_email
from blitz_api.cron_manager_api import CronManager
from cron_manager.models import Task
from blitz_api.models import Address
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from safedelete.models import SafeDeleteModel
from simple_history.models import HistoricalRecords

from log_management.models import (
    Log,
    EmailLog,
)
from store.models import (
    Membership,
    OrderLine,
    BaseProduct,
    OrderLineBaseProduct,
    OptionProduct,
    Coupon,
    Refund,
    CouponUser,
)
from store.services import refund_amount
from store.exceptions import PaymentAPIError
from store.services import PAYSAFE_EXCEPTION

User = get_user_model()
TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


class RetreatType(models.Model):

    class Meta:
        verbose_name = _("Type of retreat")
        verbose_name_plural = _("Types of retreat")
        ordering = ['index_ordering']

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    # Timedelta to show the videoconferencing link before the retreat
    minutes_before_display_link = models.IntegerField(
        verbose_name=_("Minute before displaying the link"),
    )

    number_of_tomatoes = models.PositiveIntegerField(
        verbose_name=_("Number of tomatoes"),
    )

    description = models.TextField(
        verbose_name=_("Description"),
    )

    short_description = models.TextField(
        verbose_name=_("Short description"),
    )

    duration_description = models.TextField(
        verbose_name=_("Description of duration")
    )

    cancellation_policies = models.TextField(
        verbose_name=_("Cancellation policies")
    )

    icon = models.ImageField(
        _('icon'),
        upload_to='retreat-type-icon',
        null=True,
        blank=True,
    )

    is_virtual = models.BooleanField(
        verbose_name=_("Is virtual"),
        default=False,
    )

    index_ordering = models.PositiveIntegerField(
        verbose_name=_('Index for display'),
        default=1,
    )

    know_more_link = models.TextField(
        verbose_name=_("Know more link"),
        blank=True,
        null=True,
    )

    template_id_for_welcome_message = models.CharField(
        verbose_name=_("Template ID for welcome message"),
        max_length=253,
        null=True,
        blank=True,
    )

    context_for_welcome_message = models.TextField(
        verbose_name=_("Context for welcome message"),
        default='{}',
        null=True,
        blank=True,
    )

    is_visible = models.BooleanField(
        verbose_name=_('Is visible'),
        default=True,
    )

    def __str__(self):
        return self.name


class AutomaticEmail(models.Model):
    """
    Define the automation emails that need to be automatically add to our
    cron-task when creating new instance of retreat.

    These emails will be sent to all the customer who have an active
    reservation at the specified time and with the specified template of
    email and context.
    """

    TIME_BASE_BEFORE_START = 'before_start'
    TIME_BASE_AFTER_END = 'after_end'

    TIME_BASE_CHOICES = (
        (TIME_BASE_BEFORE_START, _("Before start")),
        (TIME_BASE_AFTER_END, _("After end")),
    )

    class Meta:
        verbose_name = _("Automatic email")
        verbose_name_plural = _("Automatic emails")

    minutes_delta = models.BigIntegerField(
        verbose_name=_("Time delta in minutes"),
    )

    time_base = models.CharField(
        verbose_name=_("Time base"),
        max_length=253,
        choices=TIME_BASE_CHOICES,
    )

    template_id = models.CharField(
        verbose_name=_("Template ID"),
        max_length=253,
    )

    context = models.TextField(
        verbose_name=_("Context"),
        max_length=253,
        default='{}'
    )

    retreat_type = models.ForeignKey(
        RetreatType,
        on_delete=models.CASCADE,
        related_name='automatic_emails',
    )


class Retreat(Address, SafeDeleteModel, BaseProduct):
    """Represents a retreat physical place."""
    DOUBLE_OCCUPATION = 'double_occupation'
    SINGLE_OCCUPATION = 'single_occupation'
    DOUBLE_SINGLE_OCCUPATION = 'double_single_occupation'

    ACTIVITY_LANGUAGE = (
        ('EN', _("English")),
        ('FR', _("French")),
        ('B', _("Bilingual")),
    )

    ROOM_CHOICES = (
        (DOUBLE_OCCUPATION, _("Double occupation")),
        (SINGLE_OCCUPATION, _("Single occupation")),
        (DOUBLE_SINGLE_OCCUPATION, _("Single and double occupation")),
    )

    class Meta:
        verbose_name = _("Retreat")
        verbose_name_plural = _("Retreats")

    Address._meta.get_field('place_name').blank = True
    Address._meta.get_field('place_name').null = True
    Address._meta.get_field('postal_code').blank = True
    Address._meta.get_field('postal_code').null = True
    Address._meta.get_field('country').blank = True
    Address._meta.get_field('country').null = True
    Address._meta.get_field('state_province').blank = True
    Address._meta.get_field('state_province').null = True
    Address._meta.get_field('city').blank = True
    Address._meta.get_field('city').null = True
    Address._meta.get_field('address_line1').blank = True
    Address._meta.get_field('address_line1').null = True

    old_id = models.IntegerField(
        verbose_name=_("Id before migrate to base product"),
        null=True,
        blank=True
    )

    seats = models.PositiveIntegerField(
        verbose_name=_("Seats"),
        default=0,
    )

    @property
    def reserved_seats(self):
        return self.wait_queue_places.filter(available=True).count()

    toilet_gendered = models.BooleanField(
        null=True,
        blank=True,
        verbose_name=_("gendered toilet"),
    )

    notification_interval = models.DurationField(
        verbose_name=_(
            "Time between two reserved place notifications."
        ),
        default=timedelta(hours=24),
    )

    activity_language = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=ACTIVITY_LANGUAGE,
        verbose_name=_("Activity language"),
    )

    type = models.ForeignKey(
        RetreatType,
        on_delete=models.CASCADE,
        related_name='retreats',
    )

    videoconference_tool = models.CharField(
        verbose_name=_("Videoconference tool"),
        max_length=100,
        null=True,
        blank=True,
    )

    videoconference_link = models.TextField(
        verbose_name=_("Videoconference link"),
        null=True,
        blank=True,
    )

    room_type = models.CharField(
        null=True,
        blank=True,
        max_length=100,
        choices=ROOM_CHOICES,
        verbose_name=_("Room Type"),
    )

    min_day_refund = models.PositiveIntegerField(
        verbose_name=_("Minimum days before the event for refund"),
        blank=True,
        null=True,
    )

    refund_rate = models.PositiveIntegerField(
        verbose_name=_("Refund rate"),
        blank=True,
        null=True,
    )

    min_day_exchange = models.PositiveIntegerField(
        verbose_name=_("Minimum days before the event for exchange"),
        blank=True,
        null=True,
    )

    users = models.ManyToManyField(
        User,
        through='Reservation',
        blank=True,
        verbose_name=_("User"),
        related_name='retreats',
    )

    exclusive_memberships = models.ManyToManyField(
        Membership,
        blank=True,
        verbose_name=_("Memberships"),
        related_name='retreats',
    )

    is_active = models.BooleanField(
        verbose_name=_("Active"),
        default=False,
    )

    email_content = models.TextField(
        verbose_name=_("Email content"),
        max_length=1000,
        null=True,
        blank=True,
    )

    accessibility = models.BooleanField(
        blank=True,
        null=True,
        verbose_name=_("Accessibility"),
    )

    form_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Form URL"),
    )

    carpool_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Carpool URL"),
    )

    review_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Review URL"),
    )

    has_shared_rooms = models.BooleanField(
        blank=True,
        null=True,
    )

    require_purchase_room = models.BooleanField(
        verbose_name=_('Requires purchase of room option'),
        default=False,
    )

    hidden = models.BooleanField(
        verbose_name=_("Hidden"),
        default=False
    )

    google_maps_url = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Google maps URL"),
    )

    accessibility_detail = models.TextField(
        verbose_name=_("Accessibility Detail"),
        null=True,
        blank=True,
    )

    sub_title = models.TextField(
        blank=True,
        null=True,
        verbose_name=_("Sub Title"),
    )

    description = models.TextField(
        verbose_name=_("Description"),
        null=True,
        blank=True,
    )

    animator = models.CharField(
        verbose_name=_("animator"),
        max_length=100,
        null=True,
        blank=True,
    )

    food_vege = models.BooleanField(
        verbose_name=_("Food vege"),
        default=False
    )

    food_vegan = models.BooleanField(
        verbose_name=_("Food vegan"),
        default=False
    )

    food_allergen_free = models.BooleanField(
        verbose_name=_("Food allergen_free"),
        default=False
    )

    food_gluten_free = models.BooleanField(
        verbose_name=_("Food gluten free"),
        default=False
    )

    # Sometime we want the retreat to be shown on a specific month
    # ---
    # Ex: If retreat begin on January 29th and finish on February
    # 29th we maybe want to show it in February
    display_start_time = models.DateTimeField(
        null=False,
        blank=False,
    )

    hide_from_client_admin_panel = models.BooleanField(
        verbose_name=_("Hide from client admin panel"),
        default=False,
    )

    # Overwrite the number of tomatoes of the retreat
    # type for this value if not null
    number_of_tomatoes = models.PositiveIntegerField(
        verbose_name=_("Number of tomatoes"),
        null=True,
        blank=True,
    )

    # Allow to create event for a specific community
    is_specific_to_community = models.BooleanField(
        default=False,
    )

    community_name = models.CharField(
        max_length=300,
        null=True,
        blank=True,
    )

    community_description = models.TextField(
        null=True,
        blank=True,
    )

    # History is registered in translation.py
    # history = HistoricalRecords()

    @property
    def get_product_display_type(self):
        return _('Retreat')

    def get_number_of_tomatoes(self):
        if self.number_of_tomatoes:
            return self.number_of_tomatoes
        else:
            return self.type.number_of_tomatoes

    @property
    def start_time(self):
        dates = self.retreat_dates.all().order_by('start_time')
        if dates.count():
            return dates[0].start_time
        else:
            return None

    @property
    def end_time(self):
        dates = self.retreat_dates.all().order_by('-end_time')
        if dates.count():
            return dates[0].end_time
        else:
            return None

    @property
    def total_reservations(self):
        return self.reservations.filter(is_active=True).count()

    def free_places_for_reserve_invitations(self):
        places_for_invitations = 0
        for invitation in self.invitations.all():
            if invitation.reserve_seat:
                places_for_invitations += invitation.nb_places_free()

        return places_for_invitations

    @property
    def places_remaining(self):
        # Nb places available without invitations
        seat_remaining = \
            self.seats - self.total_reservations - self.reserved_seats

        # We remove the free places of invitation to "block" those places
        # Because we already count all invitation we remove only
        # free places and not all places reserved for invitatioons
        seat_remaining -= self.free_places_for_reserve_invitations()

        return seat_remaining if seat_remaining > 0 else 0

    @property
    def has_room_option(self):
        for opt in self.options:
            if opt.is_room_option:
                return True
        return False

    def has_places_remaining(self, selected_invitation=None):
        seat_remaining = self.places_remaining

        # add places reserved for the selected invitation
        if selected_invitation and \
                selected_invitation.reserve_seat:
            seat_remaining = \
                seat_remaining + selected_invitation.nb_places_free()

        return seat_remaining > 0

    def __str__(self):
        return self.name

    def notify_scheduler_waite_queue(self, retrat_notification_url):
        # Ask the external scheduler to start calling /notify if the
        # reserved_seats count == 1. Otherwise, the scheduler should
        # already be calling /notify at specified intervals.
        #
        # Since we are in the context of a cancelation, if reserved_seats
        # equals 1, that means that this is the first cancelation.

        if self.reserved_seats == 1:
            scheduler_url = '{0}'.format(
                settings.EXTERNAL_SCHEDULER['URL'],
            )

            data = {
                "hour": timezone.now().hour,
                "minute": (timezone.now().minute + 5) % 60,
                "url": retrat_notification_url,
                "description": "Retreat wait queue notification"
            }

            try:
                auth_data = {
                    "username": settings.EXTERNAL_SCHEDULER['USER'],
                    "password": settings.EXTERNAL_SCHEDULER['PASSWORD']
                }
                auth = requests.post(
                    scheduler_url + "/authentication",
                    json=auth_data,
                )
                auth.raise_for_status()

                r = requests.post(
                    scheduler_url + '/tasks',
                    json=data,
                    headers={
                        'Authorization':
                            'Token ' + json.loads(auth.content)[
                                'token']
                    },
                    timeout=(10, 10),
                )
                r.raise_for_status()
            except (
                    requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError) as err:
                mail_admins(
                    "Thèsez-vous: external scheduler error",
                    traceback.format_exc()
                )

    def notify_reserved_seat(self, user):
        """
        This function sends an email to notify a
        user that he has a reserved seat
        to a retreat for 24h hours.
        """
        wait_queue: WaitQueue = WaitQueue.objects.get(
            user=user,
            retreat=self,
        )

        # Setup the url for the activation button in the email
        wait_queue_url = settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'RETREAT_UNSUBSCRIBE_URL'] \
            .replace(
            "{{wait_queue_id}}",
            str(wait_queue.id)
        )

        context = {
            'USER_FIRST_NAME': user.first_name,
            'USER_LAST_NAME': user.last_name,
            'USER_EMAIL': user.email,
            'RETREAT_NAME': self.name,
            'WAIT_QUEUE_URL': wait_queue_url,
        }

        send_templated_email(
            [user],
            context,
            'WAIT_QUEUE_RESERVED_SEAT_CREATED'
        )

    def add_wait_queue_place(self, user_cancel, generate_cron=True):
        new_wait_queue_place = WaitQueuePlace.objects.create(
            retreat=self,
            cancel_by=user_cancel
        )
        if generate_cron:
            new_wait_queue_place.generate_cron_task()
        return new_wait_queue_place

    def add_user_to_wait_queue(self, user):
        return WaitQueue.objects.create(
            user=user,
            retreat=self,
        )

    def get_wait_queue_place_reserved(self, user):
        return self.wait_queue_places.filter(
            available=True,
            wait_queue_places_reserved__user=user
        ).order_by('create').first()

    def check_and_use_reserved_place(self, user):
        wait_queue_place = self.get_wait_queue_place_reserved(user)
        if wait_queue_place:
            wait_queues = self.wait_queue.filter(user=user)
            for wait_queue in wait_queues:
                wait_queue.used = True
                wait_queue.save()

            wait_queue_place.available = False
            wait_queue_place.save()

            user_places_reserved = WaitQueuePlaceReserved.objects.filter(
                wait_queue_place__retreat=self,
                user=user
            )
            for user_place_reserved in user_places_reserved:
                user_place_reserved.used = True
                user_place_reserved.save()

    def can_order_the_retreat(self, user, invitation=None):
        has_remaining_place = self.has_places_remaining(invitation)

        wait_queue_place = self.get_wait_queue_place_reserved(user)
        has_reserved_place = wait_queue_place is not None
        can_order_the_retreat = has_remaining_place or has_reserved_place

        return can_order_the_retreat

    def get_datetime_refund(self):
        return self.start_time - timedelta(
            days=self.min_day_refund)

    def set_automatic_email(self):
        """
        Create task for automatic email.
        """
        cron_manager = CronManager()
        for email in self.type.automatic_emails.all():
            if email.time_base == AutomaticEmail.TIME_BASE_BEFORE_START:
                execution_date = self.start_time
            elif email.time_base == AutomaticEmail.TIME_BASE_AFTER_END:
                execution_date = self.end_time
            else:
                raise AttributeError(_("Time based not supported."))

            if execution_date:
                try:
                    task_url = cron_manager.get_retreat_target_url(self, email)
                    task = Task.objects.get(url=task_url, active=True)
                    real_task_time = execution_date + timedelta(
                        minutes=email.minutes_delta)
                    if task.execution_datetime == real_task_time:
                        # Task exists and date is correct
                        create_task = False
                    else:
                        # Task exists and date has changed
                        create_task = True
                        task.active = False
                        task.save()
                except Task.DoesNotExist:
                    create_task = True
                if create_task:
                    execution_date += timedelta(minutes=email.minutes_delta)
                    cron_manager.create_email_task(
                        self,
                        email,
                        execution_date
                    )

    def activate(self):
        if not self.is_active:
            if not self.start_time:
                raise ValueError(
                    _("Retreat need to have a start time before activate it")
                )

            if not self.end_time:
                raise ValueError(
                    _("Retreat need to have a end time before activate it")
                )

            if self.seats <= 0:
                raise ValueError(
                    _("Retreat need to have at least one seat available")
                )

            if self.min_day_refund is None:
                raise ValueError(
                    _("Retreat need to have a minimum day refund policy")
                )

            if self.min_day_exchange is None:
                raise ValueError(
                    _("Retreat need to have a minimum day exchange policy")
                )

            if self.refund_rate is None:
                raise ValueError(
                    _("Retreat need to have a refund rate policy")
                )

            self.set_automatic_email()

            self.is_active = True
            self.save()

    @staticmethod
    def _set_participant_room(participant_data, room_number):
        participant_data['room_number'] = room_number
        participant_data['placed'] = True
        return participant_data

    def get_retreat_room_distribution(self):
        """
        Generate room distribution for a retreat, matching people with their
        friends or their preferred gender.
        Return a dict of dict with data and room number for each participant
        with participant id as key
        """
        active_reservations = self.reservations.filter(is_active=True)
        room_pool = {}
        single_pool = {}
        friend_pool = {}
        mixed_pool = {}

        current_man_room = None
        current_woman_room = None
        current_non_binary_room = None
        current_mixed_room = None

        retreat_room_distribution = {}
        room_number = 0

        for reservation in active_reservations:
            participant_data = {
                'id': reservation.user.id,
                'first_name': reservation.user.first_name,
                'last_name': reservation.user.last_name,
                'email': reservation.user.email,
                'room_option': 'single',
                'gender_preference': 'NA',
                'share_with': 'NA',
                'room_number': 0,
                'placed': False
            }
            room_options = OptionProduct.objects.filter(is_room_option=True)
            try:
                participant_order_detail = OrderLineBaseProduct.objects.get(
                    order_line=reservation.order_line,
                    option__in=room_options
                )
            except OrderLineBaseProduct.DoesNotExist:
                # User has no options for the retreat
                participant_data['room_option'] = 'NA'
                participant_data['room_number'] = 'NA'
                retreat_room_distribution[reservation.user.id] = \
                    participant_data
                continue
            current_option = OptionProduct.objects.get(
                id=participant_order_detail.option_id,
            )
            if current_option.type == OptionProduct.METADATA_SHARED_ROOM:
                participant_data['gender_preference'] = \
                    participant_order_detail.metadata[
                        'share_with_preferred_gender'
                    ]
                participant_data['room_option'] = 'shared'
                if participant_order_detail.metadata['share_with_member']:
                    participant_data['share_with'] = \
                        participant_order_detail.metadata['share_with_member']
                    friend_pool[reservation.user.email] = participant_data
                    continue
                elif participant_data['gender_preference'] == 'mixte':
                    mixed_pool[reservation.user.email] = participant_data
                    continue
                room_pool[reservation.user.email] = participant_data
            else:
                single_pool[reservation.user.email] = participant_data

        # Handling single pool
        for key, value in single_pool.items():
            if not value['placed']:
                room_number += 1
                retreat_room_distribution[value['id']] = \
                    self._set_participant_room(value, room_number)

        # Handling friend pool
        for key, value in friend_pool.items():
            if not value['placed']:
                is_in_friend_pool = value['share_with'] in friend_pool
                if is_in_friend_pool and value['share_with'] != key:
                    if friend_pool[value['share_with']]['share_with'] == key:
                        room_number += 1
                        retreat_room_distribution[value['id']] = \
                            self._set_participant_room(value, room_number)
                        roommate_id = friend_pool[value['share_with']]['id']
                        retreat_room_distribution[roommate_id] = \
                            self._set_participant_room(
                                friend_pool[value['share_with']],
                                room_number)
                        continue
                # Pairing not found, putting in other pool
                if value['gender_preference'] == 'mixte':
                    mixed_pool[key] = value
                else:
                    room_pool[key] = value

        # Handling main pool
        for key, value in room_pool.items():
            if not value['placed']:
                if value['gender_preference'] == 'man':
                    if current_man_room:
                        room_number += 1
                        retreat_room_distribution[value['id']] = \
                            self._set_participant_room(value, room_number)
                        roommate_id = room_pool[current_man_room]['id']
                        retreat_room_distribution[roommate_id] = \
                            self._set_participant_room(
                                room_pool[current_man_room],
                                room_number)
                        current_man_room = None
                    else:
                        current_man_room = key
                elif value['gender_preference'] == 'woman':
                    if current_woman_room:
                        room_number += 1
                        retreat_room_distribution[value['id']] = \
                            self._set_participant_room(value, room_number)
                        roommate_id = room_pool[current_woman_room]['id']
                        retreat_room_distribution[roommate_id] = \
                            self._set_participant_room(
                                room_pool[current_woman_room],
                                room_number)
                        current_woman_room = None
                    else:
                        current_woman_room = key
                elif value['gender_preference'] == 'non-binary':
                    if current_non_binary_room:
                        room_number += 1
                        retreat_room_distribution[value['id']] = \
                            self._set_participant_room(value, room_number)
                        roommate_id = room_pool[current_non_binary_room]['id']
                        retreat_room_distribution[roommate_id] = \
                            self._set_participant_room(
                                room_pool[current_non_binary_room],
                                room_number)
                        current_non_binary_room = None
                    else:
                        current_non_binary_room = key

        # Handling shared rooms for mixte
        for key, value in mixed_pool.items():
            # fill the rooms or create mixte room
            if current_man_room:
                room_number += 1
                retreat_room_distribution[value['id']] = \
                    self._set_participant_room(value, room_number)
                roommate_id = room_pool[current_man_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_man_room],
                        room_number)
                current_man_room = None
            elif current_woman_room:
                room_number += 1
                retreat_room_distribution[value['id']] = \
                    self._set_participant_room(value, room_number)
                roommate_id = room_pool[current_woman_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_woman_room],
                        room_number)
                current_woman_room = None
            elif current_non_binary_room:
                room_number += 1
                retreat_room_distribution[value['id']] = \
                    self._set_participant_room(value, room_number)
                roommate_id = room_pool[current_non_binary_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_non_binary_room],
                        room_number)
                current_non_binary_room = None
            elif current_mixed_room:
                room_number += 1
                retreat_room_distribution[value['id']] = \
                    self._set_participant_room(value, room_number)
                roommate_id = room_pool[current_mixed_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        mixed_pool[current_mixed_room],
                        room_number)
                current_mixed_room = None
            else:
                current_mixed_room = key

        # Handling unpaired participants
        if current_mixed_room:
            room_number += 1
            roommate_id = mixed_pool[current_mixed_room]['id']
            retreat_room_distribution[roommate_id] = \
                self._set_participant_room(
                    mixed_pool[current_mixed_room],
                    room_number)
        else:
            if current_man_room and \
                    current_woman_room and \
                    current_non_binary_room:
                room_number += 1
                roommate_id = room_pool[current_man_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_man_room],
                        room_number)
                roommate_id = room_pool[current_woman_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_woman_room],
                        room_number)
                room_number += 1
                roommate_id = room_pool[current_non_binary_room]['id']
                retreat_room_distribution[roommate_id] = \
                    self._set_participant_room(
                        room_pool[current_non_binary_room],
                        room_number)
            elif current_man_room or \
                    current_woman_room or \
                    current_non_binary_room:
                room_number += 1
                if current_man_room:
                    roommate_id = room_pool[current_man_room]['id']
                    retreat_room_distribution[roommate_id] = \
                        self._set_participant_room(
                            room_pool[current_man_room],
                            room_number)
                if current_woman_room:
                    roommate_id = room_pool[current_woman_room]['id']
                    retreat_room_distribution[roommate_id] = \
                        self._set_participant_room(
                            room_pool[current_woman_room],
                            room_number)
                if current_non_binary_room:
                    roommate_id = room_pool[current_non_binary_room]['id']
                    retreat_room_distribution[roommate_id] = \
                        self._set_participant_room(
                            room_pool[current_non_binary_room],
                            room_number)
        return retreat_room_distribution

    def get_participants_emails(self):
        """
        Return a list of participant emails
        """
        participant_emails = set()
        active_reservations = self.reservations.filter(is_active=True)
        for reservation in active_reservations:
            participant_emails.add(reservation.user.email)
        return list(participant_emails)

    def process_impacted_users(self, reason, reason_message, force_refund):
        """
        Notify and potentially refund user for a reason happening on retreat:
        Retreat cancelled, deleted ...
        If a date changes or is deleted, users must be notified and refunded so
        they can book again the retreat if they want
        """
        if self.total_reservations > 0:
            from .services import send_updated_retreat_email
            self.cancel_participants_reservation(force_refund)
            send_updated_retreat_email(
                self,
                self.get_participants_emails(),
                reason,
                reason_message,
            )

    def cancel_participants_reservation(self, force_refund):
        """
        Cancel all participants' reservation
        :params force_refund: True if we want to force refund for participants,
        otherwise regular refund will be done.
        """
        active_reservations = self.reservations.filter(is_active=True)
        refund_data = []

        # Process the refund and gather data to be sent by email
        with transaction.atomic():
            for reservation in active_reservations:
                refund_data.append(
                    reservation.process_refund(
                        Reservation.CANCELATION_REASON_RETREAT_DELETED,
                        force_refund)
                )

        # Send emails to each participant having a refund
        with transaction.atomic():
            for data in refund_data:
                if data:
                    Reservation.send_refund_confirmation_email(data)

    def custom_delete(self, deletion_message=None, force_refund=False):
        """
        Deleting a retreat sends an email to all registered participants
        set the retreat to inactive and hide it from the admin panel.
        The object itself is not destroyed.
        A refund will be made if applicable to all participants
        """
        self.is_active = False
        self.hide_from_client_admin_panel = True
        self.process_impacted_users('deletion', deletion_message, force_refund)
        self.save()


class RetreatDate(models.Model):

    class Meta:
        verbose_name = _("Retreat date")
        verbose_name_plural = _("Retreat dates")
        ordering = ["start_time"]

    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='retreat_dates',
    )

    start_time = models.DateTimeField(
        verbose_name=_("Start time"),
    )

    end_time = models.DateTimeField(
        verbose_name=_("End time"),
    )


class Picture(models.Model):
    """Represents pictures representing a retreat place"""

    class Meta:
        verbose_name = _("Picture")
        verbose_name_plural = _("Pictures")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    retreat = models.ForeignKey(
        Retreat,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Retreat"),
        related_name='pictures',
    )

    picture = models.ImageField(_('picture'), upload_to='retreats')

    # Needed to display in the admin panel
    def picture_tag(self):
        return format_html('<img href="{0}" src="{0}" height="150" />'.format(
            self.picture.url))

    picture_tag.allow_tags = True
    picture_tag.short_description = 'Picture'

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class Reservation(SafeDeleteModel):
    """Represents a user registration to a Retreat"""
    CANCELATION_REASON_USER_CANCELLED = 'U'
    CANCELATION_REASON_RETREAT_DELETED = 'RD'
    CANCELATION_REASON_RETREAT_MODIFIED = 'RM'
    CANCELATION_REASON_ADMIN_CANCELLED = 'A'

    CANCELATION_ACTION_REFUND = 'R'
    CANCELATION_ACTION_EXCHANGE = 'E'
    CANCELATION_ACTION_NONE = 'N'

    CANCELATION_REASON = (
        (CANCELATION_REASON_USER_CANCELLED, _("User canceled")),
        (CANCELATION_REASON_RETREAT_DELETED, _("Retreat deleted")),
        (CANCELATION_REASON_RETREAT_MODIFIED, _("Retreat modified")),
        (CANCELATION_REASON_ADMIN_CANCELLED, _("Admin canceled")),
    )

    CANCELATION_ACTION = (
        (CANCELATION_ACTION_REFUND, _("Refund")),
        (CANCELATION_ACTION_EXCHANGE, _("Exchange")),
        (CANCELATION_ACTION_NONE, _("None")),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='retreat_reservations',
    )
    REFUND_REASON = {
        CANCELATION_REASON_USER_CANCELLED: "Reservation canceled",
        CANCELATION_REASON_RETREAT_DELETED: "Retreat deleted",
        CANCELATION_REASON_RETREAT_MODIFIED: "Retreat modified",
        CANCELATION_REASON_ADMIN_CANCELLED: "Reservation canceled",
    }
    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='reservations',
    )
    is_active = models.BooleanField(verbose_name=_("Active"))
    cancelation_reason = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=CANCELATION_REASON,
        verbose_name=_("Cancelation reason"),
    )
    cancelation_action = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=CANCELATION_ACTION,
        verbose_name=_("Cancelation action"),
    )
    cancelation_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Cancelation date"),
    )
    is_present = models.BooleanField(
        verbose_name=_("Present"),
        default=False,
    )
    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        verbose_name=_("Order line"),
        related_name='retreat_reservations',
        null=True,
        blank=True
    )
    refundable = models.BooleanField(
        verbose_name=_("Refundable"),
        default=True,
    )
    exchangeable = models.BooleanField(
        verbose_name=_("Exchangeable"),
        default=True,
    )

    inscription_date = models.DateTimeField(
        verbose_name="Inscription date",
        auto_now_add=True
    )

    invitation = models.ForeignKey(
        'RetreatInvitation',
        on_delete=models.DO_NOTHING,
        verbose_name=_("Invitation"),
        related_name='retreat_reservations',
        null=True,
        blank=True
    )

    post_event_send = models.BooleanField(
        verbose_name=_('Post event notification send'),
        default=False
    )

    pre_event_send = models.BooleanField(
        verbose_name=_('Pre event notification send'),
        default=False
    )

    history = HistoricalRecords()

    def __str__(self):
        return str(self.user)

    def get_refund_value(self, total_refund=False):
        if self.order_line is None or self.order_line.is_made_by_admin:
            return 0

        # First get net pay: total cost
        refund_value = float(self.order_line.total_cost)
        # Add the tax rate, so we have the real value pay by the user
        refund_value *= TAX_RATE + 1.0

        if not total_refund:
            # keep only the part that the retreat allow to refund
            refund_value *= self.retreat.refund_rate / 100

        # Remove value already refund
        previous_refunds = self.order_line.refunds
        if previous_refunds:
            refund_value -= sum(
                previous_refunds.all().values_list('amount', flat=True)
            )

        return round(refund_value, 2) if refund_value > 0 else 0

    def make_refund(self, refund_reason, total_refund=False):
        amount_to_refund = self.get_refund_value(total_refund)

        # paysafe use value without cent
        amount_to_refund_paysafe = int(round(amount_to_refund * 100))

        refund_response = refund_amount(
            self.order_line.order.settlement_id,
            amount_to_refund_paysafe
        )
        refund_res_content = refund_response.json()

        refund = Refund.objects.create(
            orderline=self.order_line,
            refund_date=timezone.now(),
            amount=amount_to_refund,
            details=refund_reason,
            refund_id=refund_res_content['id'],
        )
        return refund

    @staticmethod
    def send_refund_confirmation_email(email_dict):
        """
        :params email_dict: contains all data necessary for email sending
        """
        amount = email_dict['amount']
        retreat = email_dict['retreat']
        order = email_dict['order']
        user = email_dict['user']
        total_amount = email_dict['total_amount']
        amount_tax = email_dict['amount_tax']
        # Here the price takes the applied coupon into account, if
        # applicable.
        old_retreat = {
            'price': (amount * retreat.refund_rate) / 100,
            'name': "{0}: {1}".format(
                _("Retreat"),
                retreat.name
            )
        }

        # Send order confirmation email
        merge_data = {
            'DATETIME': timezone.localtime().strftime("%x %X"),
            'ORDER_ID': order.id,
            'CUSTOMER_NAME': user.first_name + " " + user.last_name,
            'CUSTOMER_EMAIL': user.email,
            'CUSTOMER_NUMBER': user.id,
            'TYPE': "Remboursement",
            'OLD_RETREAT': old_retreat,
            'COST': total_amount,
            'TAX': amount_tax,
        }

        plain_msg = render_to_string("refund.txt", merge_data)
        msg_html = render_to_string("refund.html", merge_data)

        try:
            response_send_mail = django_send_mail(
                "Confirmation de remboursement",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=msg_html,
            )

            EmailLog.add(user.email, 'refund', response_send_mail)
        except Exception as err:
            additional_data = {
                'title': "Confirmation de remboursement",
                'default_from': settings.DEFAULT_FROM_EMAIL,
                'user_email': user.email,
                'merge_data': merge_data,
                'template': 'refund.html'
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise

    def process_refund(self, cancel_reason, force_refund):
        """
        User will be refund the retreat's "refund_rate" if we're at least
        "min_day_refund" days before the event.

        By canceling 'min_day_refund' days or more before the event, the user
         will be refunded 'refund_rate'% of the price paid.
        The user will receive an email confirming the refund or inviting the
         user to contact the support if his payment information are no longer
         valid.
        If the user cancels less than 'min_day_refund' days before the event,
         no refund is made unless forced by admin.

        Taxes are refunded proportionally to refund_rate.
        """
        retreat = self.retreat
        user = self.user
        reservation_active = self.is_active
        order_line = self.order_line
        if order_line:
            order = order_line.order
            refundable = self.refundable
        else:
            order = None
            refundable = False
        respects_minimum_days = (
                (retreat.start_time - timezone.now()) >=
                timedelta(days=retreat.min_day_refund))

        # In order to process a refund we need to be in one of those
        # two cases:
        #
        #  1 - We respect the date limit to be refund and the retreat is
        #  refundable
        #
        #  2 - An admin want to force a refund and the user paid for
        #  his reservation
        #
        # In all case, only paid reservation (amount > 0) can be refunded
        if self.get_refund_value() > 0:
            process_refund = (respects_minimum_days and refundable) or \
                             force_refund
        else:
            process_refund = False

        with transaction.atomic():
            # No need to check for previous refunds because a refunded
            # reservation is automatically canceled, thus not active.
            if reservation_active:
                if order_line and order_line.quantity > 1:
                    raise rest_framework_serializers.ValidationError({
                        'non_field_errors': [_(
                            "The order containing this reservation has a "
                            "quantity bigger than 1. Please contact the "
                            "support team."
                        )]
                    })
                if process_refund:
                    try:
                        refund = self.make_refund(
                            self.REFUND_REASON[cancel_reason])
                    except PaymentAPIError as err:
                        if str(err) == PAYSAFE_EXCEPTION['3406']:
                            raise rest_framework_serializers.ValidationError({
                                'non_field_errors': [_(
                                    "The order has not been charged yet. Try "
                                    "again later."
                                )],
                                'detail': err.detail
                            })
                        if str(err) == PAYSAFE_EXCEPTION['3404']:
                            raise rest_framework_serializers.ValidationError({
                                'non_field_errors': [_(
                                    "The order has already been refunded by "
                                    "Paysafe."
                                )],
                                'detail': err.detail
                            })
                        raise rest_framework_serializers.ValidationError(
                            {
                                'message': str(err),
                                'non_field_errors': [_(
                                    "An error occured with the payment system."
                                    " Please try again later."
                                )],
                                'detail': err.detail
                            }
                        )
                    self.cancelation_action = self.CANCELATION_ACTION_REFUND
                else:
                    self.cancelation_action = self.CANCELATION_ACTION_NONE
                self.is_active = False

                self.cancelation_reason = cancel_reason
                self.cancelation_date = timezone.now()
                self.save()

                # Rollback the coupon number of use if the reservation
                # was done with a coupon
                if order_line and order_line.coupon:
                    coupon_user = CouponUser.objects.get(
                        user=user,
                        coupon=order_line.coupon,
                    )
                    coupon_user.uses = coupon_user.uses - 1
                    coupon_user.save()

                # free seat unless retreat is deleted
                if cancel_reason != self.CANCELATION_REASON_RETREAT_DELETED:
                    free_seats = retreat.places_remaining
                    if retreat.reserved_seats or free_seats == 1:
                        retreat.add_wait_queue_place(user)
                    retreat.save()

        email_data = {}
        if reservation_active and \
                self.cancelation_action == self.CANCELATION_ACTION_REFUND:
            email_data = {
                'amount': round(refund.amount - refund.amount * TAX_RATE, 2),
                'retreat': retreat,
                'order': order,
                'user': user,
                'total_amount': refund.amount,
                'amount_tax': round(refund.amount * TAX_RATE, 2),
            }
        return email_data


class RetreatUsageLog(models.Model):
    """
    Log usage of the videoconference link for virtual activities
    """

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        verbose_name=_("Reservation"),
        related_name='usage_logs',
    )

    datetime = models.DateTimeField(
        verbose_name=_("Datetime"),
        auto_now_add=True,
    )


class AutomaticEmailLog(models.Model):

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='automatic_email_logs',
    )

    email = models.ForeignKey(
        AutomaticEmail,
        on_delete=models.CASCADE,
        related_name='automatic_email_logs',
    )

    sent_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Sent date"),
        auto_now_add=True,
    )

    @property
    def template_id(self):
        return self.email.template_id

    @property
    def retreat(self):
        return self.reservation.retreat

    @property
    def user(self):
        return self.reservation.user

    class Meta:
        verbose_name = _("Automatic email log")
        verbose_name_plural = _("Automatic email logs")


class WaitQueue(models.Model):
    """
    Represents element of a FIFO waiting queue to which users register
    manually.
    When the 'notify' action is called, first users of the queue of every
    retreat will be notified by email if there is a place left in the
    retreat.
    """

    class Meta:
        verbose_name = _("Waiting queue")
        verbose_name_plural = _("Waiting queues")
        unique_together = ('user', 'retreat')

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='wait_queues',
    )

    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='wait_queue',
    )

    used = models.BooleanField(
        verbose_name=_("Used"),
        default=False
    )

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return ', '.join([str(self.retreat), str(self.user)])


class RetreatInvitation(SafeDeleteModel):
    url_token = models.CharField(
        _("Key"),
        max_length=40,
        unique=True)

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
        blank=True,
        null=True,
    )

    nb_places = models.IntegerField(
        verbose_name=_("Number of places")
    )

    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='invitations',
    )

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        verbose_name=_("Coupon"),
        related_name='invitations',
        null=True,
        blank=True
    )

    reserve_seat = models.BooleanField(
        verbose_name=_("Should reserve seat"),
        default=False
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.url_token

    def save(self, *args, **kwargs):
        if not self.url_token:
            self.url_token = self.generate_key()
        return super(RetreatInvitation, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()

    @property
    def front_url(self):
        url = settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'RETREAT_INVITATION_URL'].replace(
            "{{token}}",
            str(self.url_token)
        )
        return url

    @property
    def nb_places_used(self):
        return self.retreat_reservations.filter(is_active=True).count()

    def nb_places_free(self):
        return self.nb_places - self.nb_places_used

    def has_free_places(self):
        return self.nb_places_used < self.nb_places


class WaitQueuePlace(models.Model):
    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='wait_queue_places',
    )
    create = models.DateTimeField(
        verbose_name=_("Create"),
        auto_now_add=True,
    )
    cancel_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("Cancel by"),
        related_name='wait_queue_places',
    )

    available = models.BooleanField(
        verbose_name=_("Available"),
        default=True
    )

    def __str__(self):
        return f'{self.retreat} {self.pk}'

    def get_user_without_places_reserved(self):
        wait_queue_places_reserved_ids = \
            self.wait_queue_places_reserved.filter(
                used=False).values('user_id')

        retreat_wait_queues = self.retreat.wait_queue\
            .filter(used=False) \
            .exclude(user_id__in=wait_queue_places_reserved_ids) \
            .order_by('created_at')

        return retreat_wait_queues

    def notify(self):

        users_notified = []

        # Stop the notification process if place not available
        if not self.available:
            return 'Wait queue place not available', True

        stop = timezone.now() >= self.retreat.start_time
        if stop:
            return 'Retreat already started', stop

        # Get all user that have no wait_queue_places_reserved
        # for this WaitQueuePlace
        retreat_wait_queues = self.get_user_without_places_reserved()

        # if we are after the refund delay, we notify every waiting user
        less_than_min_day_refund = \
            timezone.now() >= self.retreat.get_datetime_refund()

        for wait_queue in retreat_wait_queues:
            # check if the user is already notified for this retreat
            user_already_notified = WaitQueuePlaceReserved.objects.filter(
                user=wait_queue.user,
                notified=True,
                used=False,
                wait_queue_place__available=True,
                wait_queue_place__retreat=self.retreat
            ).exists()

            wait_queue_reserved = WaitQueuePlaceReserved.objects.create(
                wait_queue_place=self,
                user=wait_queue.user
            )
            if not user_already_notified:
                users_notified.append(wait_queue_reserved.notify())
                if not less_than_min_day_refund:
                    break

        return users_notified, False

    def generate_cron_task(self):
        cron_manager = CronManager()
        cron_manager.create_wait_queue_place_notification(self.id)


class WaitQueuePlaceReserved(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='wait_queue_places_reserved',
    )
    wait_queue_place = models.ForeignKey(
        WaitQueuePlace,
        on_delete=models.CASCADE,
        verbose_name=_("Wait Queue Place"),
        related_name='wait_queue_places_reserved',
    )
    create = models.DateTimeField(
        verbose_name=_("Create"),
        auto_now_add=True,
    )
    notified = models.BooleanField(
        verbose_name=_("Notified"),
        default=False
    )

    used = models.BooleanField(
        verbose_name=_("Used"),
        default=False
    )

    def __str__(self):
        return f'{self.wait_queue_place}-{self.user}'

    def notify(self):
        self.wait_queue_place.retreat.notify_reserved_seat(self.user)
        self.notified = True
        self.save()

        return self.user.email

    def available(self):
        return self.wait_queue_place.available
