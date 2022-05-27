import binascii
import os
import json
import traceback
from datetime import timedelta

import requests
from django.conf import settings
from django.core.mail import mail_admins, send_mail
from django.utils import timezone

from blitz_api.services import send_mail as send_templated_email
from blitz_api.cron_manager_api import CronManager
from blitz_api.models import Address
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from safedelete.models import SafeDeleteModel
from simple_history.models import HistoricalRecords

from store.models import (
    Membership,
    OrderLine,
    BaseProduct,
    Coupon,
    Refund,
)
from store.services import refund_amount

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

    # History is registered in translation.py
    # history = HistoricalRecords()

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

    def activate(self):
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

        cron_manager = CronManager()

        for email in self.type.automatic_emails.all():
            if email.time_base == AutomaticEmail.TIME_BASE_BEFORE_START:
                execution_date = self.start_time
            else:
                execution_date = self.end_time

            execution_date += timedelta(minutes=email.minutes_delta)

            cron_manager.create_email_task(
                self,
                email,
                execution_date
            )

        self.is_active = True
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

    CANCELATION_REASON = (
        ('U', _("User canceled")),
        ('RD', _("Retreat deleted")),
        ('RM', _("Retreat modified")),
        ('A', _("Admin canceled")),
    )

    CANCELATION_ACTION = (
        ('R', _("Refund")),
        ('E', _("Exchange")),
        ('N', _("None")),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='retreat_reservations',
    )
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
        if self.order_line is None:
            return 0

        # First get net pay: total cost
        refund_value = float(self.order_line.cost)
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
