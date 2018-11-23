from django.contrib.auth import get_user_model
from django.db import models
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from safedelete.models import SafeDeleteModel
from simple_history.models import HistoricalRecords

from blitz_api.models import Address
from store.models import Membership

User = get_user_model()


class Retirement(Address, SafeDeleteModel):
    """Represents physical places."""

    ACTIVITY_LANGUAGE = (
        ('EN', _("English")),
        ('FR', _("French")),
        ('B', _("Bilingual")),
    )

    class Meta:
        verbose_name = _("Retirement")
        verbose_name_plural = _("Retirements")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    details = models.CharField(
        verbose_name=_("Details"),
        max_length=1000,
    )

    seats = models.IntegerField(verbose_name=_("Seats"), )

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
        related_name='retirements',
    )

    exclusive_memberships = models.ManyToManyField(
        Membership,
        blank=True,
        verbose_name=_("Memberships"),
        related_name='retirements',
    )

    is_active = models.BooleanField(verbose_name=_("Active"), )

    email_content = models.TextField(
        verbose_name=_("Email content"),
        max_length=1000,
        null=True,
        blank=True,
    )

    # History is registered in translation.py
    # history = HistoricalRecords()

    @property
    def total_reservations(self):
        reservations = Reservation.objects.filter(
            retirement=self,
            is_active=True,
        ).count()
        return reservations

    def __str__(self):
        return self.name


class Picture(models.Model):
    """Represents pictures representing a retirement place"""

    class Meta:
        verbose_name = _("Picture")
        verbose_name_plural = _("Pictures")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    retirement = models.ForeignKey(
        Retirement,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Retirement"),
        related_name='pictures',
    )

    picture = models.ImageField(_('picture'), upload_to='retirements')

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
    """Represents a user registration to a TimeSlot"""

    CANCELATION_REASON = (
        ('U', _("User canceled")),
        ('RD', _("Retirement deleted")),
        ('RM', _("Retirement modified")),
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
        related_name='retirement_reservations',
    )
    retirement = models.ForeignKey(
        Retirement,
        on_delete=models.CASCADE,
        verbose_name=_("Retirement"),
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

    history = HistoricalRecords()

    def __str__(self):
        return str(self.user)
