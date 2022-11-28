import binascii
import datetime
import os
import logging

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.utils.translation import ugettext_lazy as _

from dateutil.relativedelta import relativedelta
from jsonfield import JSONField
from rest_framework.authtoken.models import Token
from simple_history.models import HistoricalRecords
from . import mailchimp

from tomato.models import Tomato
from blitz_api import services
from blitz_api.managers import ActionTokenManager

logger = logging.getLogger(__name__)


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
    membership_end_notification = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Membership end notification date"),
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

    last_acceptation_terms_and_conditions = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("Last acceptation of the terms and conditions"),
    )

    history = HistoricalRecords()

    def send_new_activation_email(self):
        if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is True:
            FRONTEND_SETTINGS = settings.LOCAL_SETTINGS[
                'FRONTEND_INTEGRATION'
            ]

            # Create an ActivationToken to activate user in the future
            activation_token = ActionToken.objects.create(
                user=self,
                type='account_activation',
                expires=timezone.now() + timezone.timedelta(
                    minutes=settings.ACTIVATION_TOKENS['MINUTES']
                )
            )

            # Setup the url for the activation button in the email
            activation_url = FRONTEND_SETTINGS['ACTIVATION_URL'].replace(
                "{{token}}",
                activation_token.key
            )

            services.send_mail(
                [self],
                {
                    "activation_url": activation_url,
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                },
                "CONFIRM_SIGN_UP",
            )

    def get_number_of_past_tomatoes(self):
        timeslots = self.get_nb_tomatoes_timeslot()
        virtual_retreats = self.get_nb_tomatoes_virtual_retreat()
        physical_retreats = self.get_nb_tomatoes_physical_retreat()

        past_count = timeslots['past'] + \
            virtual_retreats['past'] + \
            physical_retreats['past']

        custom_tomatoes = Tomato.objects.filter(
            user=self,
        ).aggregate(
            Sum('number_of_tomato'),
        )

        if custom_tomatoes['number_of_tomato__sum'] is not None:
            past_count += custom_tomatoes['number_of_tomato__sum']

        return past_count

    def get_number_of_future_tomatoes(self):
        timeslots = self.get_nb_tomatoes_timeslot()
        virtual_retreats = self.get_nb_tomatoes_virtual_retreat()
        physical_retreats = self.get_nb_tomatoes_physical_retreat()

        future_count = timeslots['future'] + \
            virtual_retreats['future'] + \
            physical_retreats['future']

        return future_count

    def get_nb_tomatoes_timeslot(self):
        from workplace.models import Reservation as TimeslotReservation

        reservations = TimeslotReservation.objects.filter(
            user=self,
            is_active=True,
        )

        past_count = 0
        future_count = 0

        for reservation in reservations:
            if reservation.timeslot.end_time < timezone.now():
                past_count += settings.NUMBER_OF_TOMATOES_TIMESLOT
            else:
                future_count += settings.NUMBER_OF_TOMATOES_TIMESLOT

        return {
            'past': past_count,
            'future': future_count,
        }

    def get_nb_tomatoes_virtual_retreat(self):
        from retirement.models import Reservation as RetreatReservation

        reservations = RetreatReservation.objects.filter(
            user=self,
            is_active=True,
            retreat__type__is_virtual=True,
        )

        past_count = 0
        future_count = 0

        for reservation in reservations:
            if reservation.retreat.end_time < timezone.now():
                past_count += reservation.retreat.get_number_of_tomatoes()
            else:
                future_count += reservation.retreat.get_number_of_tomatoes()

        return {
            'past': past_count,
            'future': future_count,
        }

    def get_nb_tomatoes_physical_retreat(self):
        from retirement.models import Reservation as RetreatReservation

        reservations = RetreatReservation.objects.filter(
            user=self,
            is_active=True,
            retreat__type__is_virtual=False,
        )

        past_count = 0
        future_count = 0

        for reservation in reservations:
            if reservation.retreat.end_time < timezone.now():
                past_count += reservation.retreat.get_number_of_tomatoes()
            else:
                future_count += reservation.retreat.get_number_of_tomatoes()

        return {
            'past': past_count,
            'future': future_count,
        }

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

    def has_membership_active(self):
        today = timezone.now().date()
        return \
            self.membership and \
            self.membership_end and \
            self.membership_end >= today

    def has_to_receive_notification(self):
        if self.has_membership_active():
            today = timezone.now().date()
            date_to_notify = self.membership_end - relativedelta(days=28)
            # check if last notification between today and last week
            if self.membership_end_notification:
                already_notify = \
                    today >= \
                    self.membership_end_notification.date() >= \
                    today - relativedelta(weeks=1)
            else:
                already_notify = False
            # To prevent spam, we need to haven't send a
            # notification in the last week and be at 28 days from the end
            return date_to_notify == today and not already_notify

    def check_and_notify_renew_membership(self):

        if self.has_to_receive_notification():
            services.notify_user_of_renew_membership(
                user=self,
                membership_end=self.membership_end.strftime('%Y-%m-%d')
            )
            return True
        return False

    def credit_tickets(self, nb_tickets: int):
        self.tickets += nb_tickets
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
    EXPORT_ANONYMOUS_CHRONO_DATA = 'ANONYMOUS CHRONO DATA'
    EXPORT_OTHER = 'OTHER'
    EXPORT_RETREAT_SALES = 'RETREAT SALES'
    EXPORT_RETREAT_PARTICIPATION = 'RETREAT PARTICIPATION'
    EXPORT_RETREAT_OPTIONS = 'RETREAT OPTIONS'

    EXPORT_CHOICES = (
        (EXPORT_ANONYMOUS_CHRONO_DATA, _('Anonymous Chrono data')),
        (EXPORT_OTHER, _('Other')),
        (EXPORT_RETREAT_SALES, _('Retreat sales')),
        (EXPORT_RETREAT_PARTICIPATION, _('Retreat participation')),
        (EXPORT_RETREAT_OPTIONS, _('Retreat options')),
    )

    file = models.FileField(
        verbose_name='file',
        upload_to='export/%Y/%m/'
    )

    name = models.CharField(
        max_length=512,
        blank=True,
        null=True
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Author'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    type = models.CharField(
        max_length=255,
        choices=EXPORT_CHOICES,
        default=EXPORT_OTHER,
    )

    def __str__(self):
        return self.name if self.name else str(self.id)

    @property
    def size(self):
        return self.file.size if self.file else None

    def send_confirmation_email(self):
        if self.author:
            services.send_mail(
                [self.author],
                {
                    "USER_FIRST_NAME": self.author.first_name,
                    "USER_LAST_NAME": self.author.last_name,
                    "export_link": self.file.url,
                },
                "EXPORT_DONE",
            )
