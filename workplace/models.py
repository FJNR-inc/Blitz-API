from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from safedelete.models import SafeDeleteModel

from simple_history.models import HistoricalRecords

from blitz_api.models import Address

User = get_user_model()


class Workplace(Address, SafeDeleteModel):
    """Represents physical places."""

    class Meta:
        verbose_name = _("Workplace")
        verbose_name_plural = _("Workplaces")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    details = models.CharField(
        verbose_name=_("Details"),
        max_length=1000,
    )

    seats = models.IntegerField(
        verbose_name=_("Seats"),
    )

    volunteers = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Volunteer"),
        related_name='workplaces',
    )

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class Picture(models.Model):
    """Represents pictures representing a workplace"""

    class Meta:
        verbose_name = _("Picture")
        verbose_name_plural = _("Pictures")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    workplace = models.ForeignKey(
        Workplace,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Workplace"),
        related_name='pictures',
    )

    picture = models.ImageField(
        _('picture'),
        upload_to='workplaces'
    )

    # Needed to display in the admin panel
    def picture_tag(self):
        return format_html(
            '<img href="{0}" src="{0}" height="150" />'
            .format(self.picture.url)
        )

    picture_tag.allow_tags = True
    picture_tag.short_description = 'Picture'

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class Period(SafeDeleteModel):
    """Represents periods of time that has certain attributes"""

    class Meta:
        verbose_name = _("Period")
        verbose_name_plural = _("Periods")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    workplace = models.ForeignKey(
        Workplace,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Workplace"),
        related_name='periods',
    )

    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Price"),
    )

    start_date = models.DateTimeField(
        verbose_name=_("Start Date"),
        blank=True,
    )

    end_date = models.DateTimeField(
        verbose_name=_("End Date"),
        blank=True,
    )

    is_active = models.BooleanField(
        verbose_name=_("Activation"),
        default=False,
    )

    @property
    def total_reservations(self):
        reservations = Reservation.objects.filter(
            timeslot__period=self,
            is_active=True,
        ).count()
        return reservations

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class TimeSlot(SafeDeleteModel):
    """Represents time slots in a day"""

    class Meta:
        verbose_name = _("Time slot")
        verbose_name_plural = _("Time slots")

    name = models.CharField(
        verbose_name=_("Name"),
        blank=True,
        null=True,
        max_length=253,
    )

    period = models.ForeignKey(
        Period,
        on_delete=models.CASCADE,
        verbose_name=_("Period"),
        related_name='time_slots',
    )

    users = models.ManyToManyField(
        User,
        through='Reservation',
        blank=True,
        verbose_name=_("User"),
        related_name='time_slots',
    )

    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Price"),
        blank=True,
        null=True,
    )

    start_time = models.DateTimeField(
        verbose_name=_("Start time"),
    )

    end_time = models.DateTimeField(
        verbose_name=_("End time"),
    )

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return str(self.start_time) + " - " + str(self.end_time)

    @property
    def billing_price(self):
        if self.price:
            return self.price
        else:
            return self.period.price

    @property
    def duration(self):
        """
        Return duration of timeslot in seconds
        """
        return int((self.end_time - self.start_time).total_seconds())

    @property
    def number_of_tomatoes(self):
        """
        Return the number of tomatoes obtained by attending this Timeslot
        1 hour = 1 tomato, we don't count minutes.
        """
        return int(self.duration // 3600)


class Reservation(SafeDeleteModel):
    """Represents a user registration to a TimeSlot"""
    CANCELATION_REASON_USER_CANCELLED = 'U'
    CANCELATION_REASON_TIMESLOT_DELETED = 'TD'
    CANCELATION_REASON_TIMESLOT_MODIFIED = 'TM'
    CANCELATION_REASON_ADMIN_CANCELLED = 'A'

    CANCELATION_REASON = (
        (CANCELATION_REASON_USER_CANCELLED, _("User canceled")),
        (CANCELATION_REASON_TIMESLOT_DELETED, _("Timeslot deleted")),
        (CANCELATION_REASON_TIMESLOT_MODIFIED, _("Timeslot modified")),
        (CANCELATION_REASON_ADMIN_CANCELLED, _("Admin canceled")),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='reservations',
    )
    timeslot = models.ForeignKey(
        TimeSlot,
        on_delete=models.CASCADE,
        verbose_name=_("Time slot"),
        related_name='reservations',
    )
    is_active = models.BooleanField(
        verbose_name=_("Active")
    )
    cancelation_reason = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=CANCELATION_REASON,
        verbose_name=_("Cancelation reason"),
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

    history = HistoricalRecords()

    def __str__(self):
        return str(self.user)

    def credit_tomatoes(self):
        """
        Credit tomatoes to user if he is present or remove them if updated
        back to not present
        """
        from tomato.models import Tomato
        reservation_type = ContentType.objects.get_for_model(
            Reservation)
        if self.is_present:
            # user presence set to True: Add tomato for the timeslot
            t, created = Tomato.objects.get_or_create(
                user=self.user,
                number_of_tomato=self.timeslot.number_of_tomatoes,
                source=Tomato.TOMATO_SOURCE_TIMESLOT,
                content_type=reservation_type,
                object_id=self.id,
            )
        else:
            # User presence set to False: remove tomato for timeslot if exists
            try:
                Tomato.objects.get(
                    user=self.user,
                    source=Tomato.TOMATO_SOURCE_TIMESLOT,
                    content_type=reservation_type,
                    object_id=self.id,
                ).delete()
            except Tomato.DoesNotExist:
                pass

    def save(self, *args, **kwargs):
        old_presence = None
        if self.pk:
            old_presence = Reservation.objects.get(pk=self.id).is_present
        super(Reservation, self).save(*args, **kwargs)
        if self.pk and old_presence != self.is_present:
            self.credit_tomatoes()
