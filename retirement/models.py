from datetime import timedelta

from blitz_api.models import Address
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from safedelete.models import SafeDeleteModel
from simple_history.models import HistoricalRecords
from store.models import Membership, OrderLine

User = get_user_model()


class Retreat(Address, SafeDeleteModel):
    """Represents a retreat physical place."""

    ACTIVITY_LANGUAGE = (
        ('EN', _("English")),
        ('FR', _("French")),
        ('B', _("Bilingual")),
    )

    class Meta:
        verbose_name = _("Retreat")
        verbose_name_plural = _("Retreats")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    details = models.CharField(
        verbose_name=_("Details"),
        max_length=1000,
    )

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

    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Price"),
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

    def __str__(self):
        return self.name


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
