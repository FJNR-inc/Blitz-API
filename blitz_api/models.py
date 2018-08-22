import binascii
import os
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from rest_framework.authtoken.models import Token

from simple_history import register
from simple_history.models import HistoricalRecords

from django.utils.translation import ugettext_lazy as _

from .managers import ActionTokenManager


class User(AbstractUser):
    """Abstraction of the base User model. Needed to extend in the future."""

    GENDER_CHOICES = (
        ('M', _("Male")),
        ('F', _("Female")),
        ('T', _("Trans")),
        ('A', _("Do not wish to identify myself")),
    )

    phone = models.CharField(
        verbose_name=_("Phone number"),
        blank=True,
        null=True,
        max_length=17,
    )
    other_phone = models.CharField(
        verbose_name=_("Other number"),
        blank=True,
        null=True,
        max_length=17,
    )
    university = models.ForeignKey(
        'Organization',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    academic_level = models.ForeignKey(
        'AcademicLevel',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Academic level"),
    )
    academic_field = models.ForeignKey(
        'AcademicField',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Academic field"),
    )
    birthdate = models.DateField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_("Birthdate"),
    )
    gender = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=GENDER_CHOICES,
        verbose_name=_("Gender"),
    )
    membership = models.ForeignKey(
        'store.Membership',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Membership"),
    )
    membership_end = models.DateField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_("Membership end date"),
    )
    tickets = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=_("Tickets"),
    )
    history = HistoricalRecords()


class TemporaryToken(Token):
    """Subclass of Token to add an expiration time."""

    class Meta:
        verbose_name = _("Temporary token")
        verbose_name_plural = _("Temporary tokens")

    expires = models.DateTimeField(
        verbose_name=_("Expiration date"),
        blank=True,
    )

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires = timezone.now() + timezone.timedelta(
                minutes=settings.REST_FRAMEWORK_TEMPORARY_TOKENS['MINUTES']
            )

        super(TemporaryToken, self).save(*args, **kwargs)

    @property
    def expired(self):
        """Returns a boolean indicating token expiration."""
        return self.expires <= timezone.now()

    def expire(self):
        """Expires a token by setting its expiration date to now."""
        self.expires = timezone.now()
        self.save()


class ActionToken(models.Model):
    """
        Class of Token to allow User to do some action.

        Generally, the token is sent by email and serves
        as a "right" to do a specific action.
    """

    ACTIONS_TYPE = [
        ('account_activation', _('Account activation')),
        ('password_change', _('Password change')),
    ]

    key = models.CharField(
        verbose_name="Key",
        max_length=40,
        primary_key=True
    )

    type = models.CharField(
        verbose_name='Type of action',
        max_length=100,
        choices=ACTIONS_TYPE,
        null=False,
    )

    user = models.ForeignKey(
        User,
        related_name='activation_token',
        on_delete=models.CASCADE,
        verbose_name="User"
    )

    created = models.DateTimeField(
        verbose_name="Creation date",
        auto_now_add=True
    )

    expires = models.DateTimeField(
        verbose_name="Expiration date",
        blank=True,
    )

    objects = ActionTokenManager()

    history = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
            self.expires = timezone.now() + timezone.timedelta(
                minutes=settings.ACTIVATION_TOKENS['MINUTES']
            )
        return super(ActionToken, self).save(*args, **kwargs)

    @staticmethod
    def generate_key():
        """Generate a new key"""
        return binascii.hexlify(os.urandom(20)).decode()

    @property
    def expired(self):
        """Returns a boolean indicating token expiration."""
        return self.expires <= timezone.now()

    def expire(self):
        """Expires a token by setting its expiration date to now."""
        self.expires = timezone.now()
        self.save()

    def __str__(self):
        return self.key


class Organization(models.Model):
    """Represents an existing organization such as an university"""

    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=100,
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Domain(models.Model):
    """An internet domain name like fsf.org"""

    class Meta:
        verbose_name = _('Domain')
        verbose_name_plural = _('Domains')

    # Full domain name may not exceed 253 characters in its textual
    # representation :
    # https://en.wikipedia.org/wiki/Domain_Name_System#Domain_name_syntax
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    example = models.CharField(
        verbose_name=_("Email example"),
        null=True,
        blank=True,
        max_length=253,
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="domains",
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class AcademicLevel(models.Model):
    """Academic level such as college or university"""

    class Meta:
        verbose_name = _('Academic level')
        verbose_name_plural = _('Academic levels')

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=100,
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class AcademicField(models.Model):
    """Academic field such as engineering or health"""

    class Meta:
        verbose_name = _('Academic field')
        verbose_name_plural = _('Academic fields')

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=100,
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Address(models.Model):
    """Abstract model for address"""
    country = models.CharField(
        max_length=45,
        blank=False,
        verbose_name=_("Country"),
    )

    state_province = models.CharField(
        max_length=55,
        blank=False,
        verbose_name=_("State/Province"),
    )
    city = models.CharField(
        max_length=50,
        blank=False,
        verbose_name=_("City"),
    )
    address_line1 = models.CharField(
        max_length=45,
        verbose_name=_("Address line 1"),
    )
    address_line2 = models.CharField(
        max_length=45,
        null=True,
        verbose_name=_("Address line 2"),
    )
    postal_code = models.CharField(
        max_length=10,
        verbose_name=_("Postal code"),
    )
    latitude = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Latitude"),
    )
    longitude = models.FloatField(
        blank=True,
        null=True,
        verbose_name=_("Longitude"),
    )
    timezone = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        verbose_name=_("Timezone"),
    )

    history = HistoricalRecords()

    class Meta:
        abstract = True
