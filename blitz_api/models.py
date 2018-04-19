from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from rest_framework.authtoken.models import Token

from django.utils.translation import ugettext_lazy as _


class User(AbstractUser):
    """Abstraction of the base User model. Needed to extend in the future."""
    pass


class TemporaryToken(Token):
    """Subclass of Token to add an expiration time."""

    class Meta:
        verbose_name = _('Temporary token')
        verbose_name_plural = _('Temporary tokens')

    expires = models.DateTimeField(
        verbose_name=_("Expiration date"),
        blank=True,
    )

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


class Organization(models.Model):
    """Represents an existing organization such as an university"""

    class Meta:
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=100,
    )

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

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="domains",
    )

    def __str__(self):
        return self.name
