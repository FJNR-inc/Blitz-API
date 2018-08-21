from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import format_html
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation
)
from django.contrib.contenttypes.models import ContentType

from blitz_api.models import AcademicLevel

User = get_user_model()


class Order(models.Model):
    """Represents a transaction."""

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='orders',
    )

    transaction_date = models.DateTimeField(
        verbose_name=_("Transaction date"),
    )

    authorization_id = models.CharField(
        verbose_name=_("Authorization ID"),
        max_length=253,
    )

    settlement_id = models.CharField(
        verbose_name=_("Settlement ID"),
        max_length=253,
    )

    @property
    def total_cost(self):
        cost = 0
        for orderline in self.order_lines.all():
            cost += orderline.content_object.price * orderline.quantity
        return float(cost)

    def __str__(self):
        return str(self.authorization_id)


class OrderLine(models.Model):
    """
    Represents a line of an order. Can specify the product/service with a
    generic relationship.
    """

    class Meta:
        verbose_name = _("Order line")
        verbose_name_plural = _("Order lines")

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )

    object_id = models.PositiveIntegerField()

    content_object = GenericForeignKey(
        'content_type',
        'object_id'
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        verbose_name=_("Order"),
        related_name='order_lines',
    )

    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
    )

    def __str__(self):
        return str(self.content_object) + ', qt:' + str(self.quantity)


class BaseProduct(models.Model):
    """Abstract model for base products"""

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    available = models.BooleanField(
        verbose_name=_("Available")
    )

    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Price"),
    )

    details = models.CharField(
        verbose_name=_("Details"),
        max_length=1000,
        null=True,
        blank=True,
    )

    order_lines = GenericRelation(OrderLine)

    class Meta:
        abstract = True


class Membership(BaseProduct):
    """Represents a membership."""

    class Meta:
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")

    duration = models.DurationField()

    academic_levels = models.ManyToManyField(
        AcademicLevel,
        blank=True,
        verbose_name=_("Academic levels"),
        related_name='memberships',
    )

    def __str__(self):
        return self.name


class Package(BaseProduct):
    """Represents a reservation package."""

    class Meta:
        verbose_name = _("Package")
        verbose_name_plural = _("Packages")

    reservations = models.PositiveIntegerField(
        verbose_name=_("Reservations"),
    )

    exclusive_memberships = models.ManyToManyField(
        Membership,
        blank=True,
        verbose_name=_("Memberships"),
        related_name='packages',
    )

    def __str__(self):
        return self.name


class CreditCard(models.Model):
    """Represents a credit card."""

    class Meta:
        verbose_name = _("Credit card")
        verbose_name_plural = _("Credit cards")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='credit_cards',
    )

    expiry_date = models.DateTimeField(
        verbose_name=_("Expiration date"),
    )

    number = models.CharField(
        verbose_name=_("Number"),
        max_length=253,
    )

    external_api_id = models.CharField(
        verbose_name=_("Number"),
        max_length=253,
    )

    def __str__(self):
        return self.name


class PaymentProfile(models.Model):
    """Represents a payment profile linked to an external payment API."""

    class Meta:
        verbose_name = _("Payment profile")
        verbose_name_plural = _("Payment profiles")

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='payment_profiles',
    )

    external_api_id = models.CharField(
        verbose_name=_("External profile ID"),
        max_length=253,
    )

    external_api_url = models.CharField(
        verbose_name=_("External profile url"),
        max_length=253,
    )

    def __str__(self):
        return self.name
