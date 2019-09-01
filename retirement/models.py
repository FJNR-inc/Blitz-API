import binascii
import os
import json
import traceback
from datetime import timedelta

from django.conf import settings

import requests
from django.conf import settings
from django.core.mail import mail_admins, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.reverse import reverse

from blitz_api.models import Address
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from safedelete.models import SafeDeleteModel
from simple_history.models import HistoricalRecords
from store.models import Membership, OrderLine, BaseProduct,\
    Coupon

User = get_user_model()


class Retreat(Address, SafeDeleteModel, BaseProduct):
    """Represents a retreat physical place."""

    ACTIVITY_LANGUAGE = (
        ('EN', _("English")),
        ('FR', _("French")),
        ('B', _("Bilingual")),
    )

    class Meta:
        verbose_name = _("Retreat")
        verbose_name_plural = _("Retreats")

    old_id = models.IntegerField(
        verbose_name=_("Id before migrate to base product"),
        null=True,)

    seats = models.IntegerField(verbose_name=_("Seats"), )

    # number of seats reserved for people in queue
    # when someone cancels their reservation and there is a queue,
    # reserved_seat is incremented by 1. If reserved_seats > 0, only
    # people with a waitQueueNotification can order a reservation
    reserved_seats = models.IntegerField(
        verbose_name=_("Reserved seats"),
        default=0,
    )

    next_user_notified = models.PositiveIntegerField(
        verbose_name=_(
            "Index of the user to be notified next for a resserved place."
        ),
        default=0,
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

    start_time = models.DateTimeField(verbose_name=_("Start time"), )

    end_time = models.DateTimeField(verbose_name=_("End time"), )

    min_day_refund = models.PositiveIntegerField(
        verbose_name=_("Minimum days before the event for refund"), )

    refund_rate = models.PositiveIntegerField(verbose_name=_("Refund rate"), )

    min_day_exchange = models.PositiveIntegerField(
        verbose_name=_("Minimum days before the event for exchange"), )

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

    is_active = models.BooleanField(verbose_name=_("Active"), )

    email_content = models.TextField(
        verbose_name=_("Email content"),
        max_length=1000,
        null=True,
        blank=True,
    )

    accessibility = models.BooleanField(verbose_name=_("Accessibility"), )

    form_url = models.CharField(
        blank=True,
        null=True,
        max_length=2000,  # Max URL length supported by IE
        verbose_name=_("Form URL"),
    )

    carpool_url = models.CharField(
        blank=True,
        null=True,
        max_length=2000,  # Max URL length supported by IE
        verbose_name=_("Carpool URL"),
    )

    review_url = models.CharField(
        blank=True,
        null=True,
        max_length=2000,  # Max URL length supported by IE
        verbose_name=_("Review URL"),
    )

    has_shared_rooms = models.BooleanField()

    hidden = models.BooleanField(
        verbose_name=_("Hidden"),
        default=False
    )

    # History is registered in translation.py
    # history = HistoricalRecords()

    @property
    def total_reservations(self):
        reservations = Reservation.objects.filter(
            retreat=self,
            is_active=True,
        ).count()
        return reservations

    @property
    def places_remaining(self):
        seats = self.seats
        reserved_seats = self.reserved_seats
        reservations = self.reservations.filter(is_active=True).count()
        return seats - reservations - reserved_seats

    def has_places_remaining(self):
        return (self.seats -
                self.total_reservations -
                self.reserved_seats) > 0

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
                                'token']},
                    timeout=(10, 10),
                )
                r.raise_for_status()
            except (requests.exceptions.HTTPError,
                    requests.exceptions.ConnectionError) as err:
                mail_admins(
                    "Thèsez-vous: external scheduler error",
                    traceback.format_exc()
                )

    def notify_users(self):
        notified_someone = False

        datetime_refund = self.start_time - timedelta(days=self.min_day_refund)
        # if we are after the refund delay, we notify every waiting user
        if timezone.now() >= datetime_refund:

            for wait_queue in self.wait_queue.all():
                user = wait_queue.user

                self.notify_reserved_seat(user)
                notified_someone = True

            # set seat and user_index to 0 because we notify everyone
            self.reserved_seats = 0

        else:
            # Get the wait queue with elements ordered by ascending date
            wait_queue = self.wait_queue.all().order_by('created_at')
            # Get number of waiting users
            nb_waiting_users = wait_queue.count()
            # If all users have already been notified, free all reserved seats
            if self.next_user_notified >= nb_waiting_users:
                self.reserved_seats = 0
                self.next_user_notified = 0
            # Else notify a user for every reserved seat
            for seat in range(self.reserved_seats):
                if self.next_user_notified >= nb_waiting_users:
                    self.reserved_seats -= 1
                else:
                    user = wait_queue[self.next_user_notified].user
                    self.notify_reserved_seat(user)
                    self.next_user_notified += 1
                    WaitQueueNotification.objects.create(
                        user=user,
                        retreat=self,
                    )
                    notified_someone = True

        self.save()
        return notified_someone

    def notify_reserved_seat(self, user):
        """
        This function sends an email to notify a
        user that he has a reserved seat
        to a retreat for 24h hours.
        """

        merge_data = {'RETREAT_NAME': self.name}

        plain_msg = render_to_string("reserved_place.txt", merge_data)
        msg_html = render_to_string("reserved_place.html", merge_data)

        return send_mail(
            "Place exclusive pour 24h",
            plain_msg,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=msg_html,
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

    history = HistoricalRecords()

    def __str__(self):
        return str(self.user)


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

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return ', '.join([str(self.retreat), str(self.user)])


class WaitQueueNotification(models.Model):
    """
    Represents a notification instance for the retreat wait queues.
    Each time a user is notified, we create an instance of this object as a
    journal. Sent notifications can then be listed by admins.
    """

    class Meta:
        verbose_name = _("Wait queue notification")
        verbose_name_plural = _("Wait queue notification")

    retreat = models.ForeignKey(
        Retreat,
        on_delete=models.CASCADE,
        verbose_name=_("Retreat"),
        related_name='wait_queue_notifications',
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='wait_queue_notifications',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return ', '.join(
            [str(self.retreat), str(self.user)]
        )


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
            'FORGOT_PASSWORD_URL'].replace(
            "{{token}}",
            str(self.url_token)
        )
        return url

    @property
    def nb_places_used(self):

        return self.retreat_reservations.filter(is_active=True).count()

    def has_free_places(self):
        return self.nb_places_used < self.nb_places
