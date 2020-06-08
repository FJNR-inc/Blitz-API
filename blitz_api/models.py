import binascii
import datetime
import os
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from jsonfield import JSONField

from rest_framework.authtoken.models import Token

from simple_history import register
from simple_history.models import HistoricalRecords

from django.utils.translation import ugettext_lazy as _

from . import mailchimp
from .managers import ActionTokenManager


class User(AbstractUser):
    """Abstraction of the base User model. Needed to extend in the future."""
    LANGUAGE_FR = 'fr'
    LANGUAGE_EN = 'en'

    GENDER_CHOICES = (
        ('M', _("Male")),
        ('F', _("Female")),
        ('T', _("Trans")),
        ('A', _("Do not wish to identify myself")),
    )
    LANGUAGE_CHOICES = (
        (LANGUAGE_EN, _('English')),
        (LANGUAGE_FR, _('French')),
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
    academic_program_code = models.CharField(
        verbose_name=_("Academic program code"),
        blank=True,
        null=True,
        max_length=17,
    )
    faculty = models.CharField(
        verbose_name=_("Faculty"),
        blank=True,
        null=True,
        max_length=100,
    )
    student_number = models.CharField(
        verbose_name=_("Student number"),
        blank=True,
        null=True,
        max_length=17,
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
    language = models.CharField(
        max_length=100,
        choices=LANGUAGE_CHOICES,
        verbose_name=_("Language"),
        null=True,
        blank=True
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
    number_of_free_virtual_retreat = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Number of free virtual retreat"),
    )
    city = models.CharField(
        verbose_name=_("City"),
        blank=True,
        null=True,
        max_length=50,
    )
    personnal_restrictions = models.TextField(
        verbose_name=_("Personnal restrictions"),
        blank=True,
        null=True,
    )

    hide_newsletter = models.BooleanField(
        default=False,
        verbose_name=_("Hide newsletter"),
    )

    history = HistoricalRecords()

    def get_active_membership(self):
        if self.membership_end and self.membership_end > datetime.date.today():
            return self.membership
        else:
            return None

    @property
    def is_in_newsletter(self):
        return mailchimp.is_email_on_list(self.email)

    @classmethod
    def create_user(cls,
                    first_name,
                    last_name,
                    birthdate,
                    gender,
                    email,
                    password,
                    academic_level=None,
                    university=None,
                    academic_field=None):

        user = User.objects.create(
            first_name=first_name[:30],
            last_name=last_name[:150],
            birthdate=birthdate,
            gender=gender,
            username=email,
            email=email,
            is_active=True,
            tickets=1,
        )
        user.set_password(password)

        if university:
            try:
                university = Organization.objects.get(pk=university)
                user.university = university
                user.save()
            except Organization.DoesNotExist:
                raise ValueError(
                    'Organization "%s" does not exist' % university)

        if academic_field:
            try:
                academic_field = AcademicField.objects.get(
                    pk=academic_field)
                user.academic_field = academic_field
                user.save()
            except AcademicField.DoesNotExist:
                raise ValueError('AcademicField "%s" does not exist' %
                                 academic_field)

        if academic_level:
            try:
                academic_level = AcademicLevel.objects.get(
                    pk=academic_level)
                user.academic_level = academic_level
                user.save()
            except AcademicLevel.DoesNotExist:
                raise ValueError('AcademicLevel "%s" does not exist' %
                                 academic_level)

        return user

    def offer_free_membership(self, membership):
        from store.models import Membership

        if not self.membership:
            try:
                membership = Membership.objects.get(pk=membership)
                self.membership = membership
            except Membership.DoesNotExist:
                raise ValueError(
                    'Membership "%s" does not exist' % membership)

        today = timezone.now().date()
        if self.membership_end and self.membership_end > today:
            self.membership_end = \
                self.membership_end + self.membership.duration
        else:
            self.membership_end = (
                    today + self.membership.duration
            )
        self.save()


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
        if not self.expires:
            self.expires = timezone.now() + timezone.timedelta(
                minutes=settings.REST_FRAMEWORK_TEMPORARY_TOKENS['MINUTES']
            )

        return super(TemporaryToken, self).save(*args, **kwargs)

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
        ('email_change', _('Email change')),
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

    data = JSONField(
        null=True
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

    # History is registered in translation.py
    # history = HistoricalRecords()

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

    # History is registered in translation.py
    # history = HistoricalRecords()

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

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class Address(models.Model):
    """Abstract model for address"""
    place_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Place name"),
    )

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
        blank=True,
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

    class Meta:
        abstract = True


class ExportMedia(models.Model):
    file = models.FileField(
        verbose_name='file',
        upload_to='export/%Y/%m/'
    )

    def __str__(self):
        return self.file.name
