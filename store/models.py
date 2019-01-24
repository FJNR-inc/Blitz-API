import decimal
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation
)
from django.contrib.contenttypes.models import ContentType

from safedelete.models import SafeDeleteModel

from simple_history.models import HistoricalRecords

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

    reference_number = models.CharField(
        verbose_name=_("Reference number"),
        max_length=253,
        null=True,
        blank=True,
    )

    history = HistoricalRecords()

    @property
    def total_cost(self):
        cost = 0
        orderlines = self.order_lines.filter(
            models.Q(content_type__model='membership') |
            models.Q(content_type__model='package') |
            models.Q(content_type__model='retirement')
        )
        for orderline in orderlines:
            cost += orderline.cost * orderline.quantity
        return cost

    @property
    def total_ticket(self):
        tickets = 0
        orderlines = self.order_lines.filter(
            content_type__model='timeslot'
        )
        for orderline in orderlines:
            tickets += orderline.content_object.price * orderline.quantity
        return tickets

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

    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.CASCADE,
        verbose_name=_("Applied coupon"),
        related_name='order_lines',
        null=True,
        blank=True,
    )

    coupon_real_value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Coupon real value"),
        default=0,
    )

    cost = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Orderline cost"),
        default=0,
    )

    history = HistoricalRecords()

    def __str__(self):
        return str(self.content_object) + ', qt:' + str(self.quantity)


class Refund(SafeDeleteModel):
    """
    Represents a refund. It is always linked to an orderline and it can refund
    it fully or partially.
    """

    class Meta:
        verbose_name = _("Refund")
        verbose_name_plural = _("Refunds")

    orderline = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        verbose_name=_("Orderline"),
        related_name='refunds',
    )

    amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Amount"),
    )

    details = models.TextField(
        verbose_name=_("Details"),
        max_length=1000,
        null=True,
        blank=True,
    )

    refund_date = models.DateTimeField(
        verbose_name=_("Refund date"),
    )

    history = HistoricalRecords()

    def __str__(self):
        return str(self.orderline) + ', ' + str(self.amount) + "$"


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

    # History is registered in translation.py
    # history = HistoricalRecords()

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

    # History is registered in translation.py
    # history = HistoricalRecords()

    def __str__(self):
        return self.name


class CustomPayment(models.Model):
    """
    Represents a custom payment that is not directly related to a product.
    Used for manual custom transactions.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='custom_payments',
    )

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Price"),
    )

    details = models.TextField(
        verbose_name=_("Details"),
        max_length=1000,
        null=True,
        blank=True,
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

    reference_number = models.CharField(
        verbose_name=_("Reference number"),
        max_length=253,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Custom payment")
        verbose_name_plural = _("Custom payments")

    history = HistoricalRecords()

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

    history = HistoricalRecords()

    def __str__(self):
        return self.name


class Coupon(SafeDeleteModel):
    """
    Represents a coupon that provides a discount on various products.
    The "owner" of the instance is the buyer of the coupon, but not necessarily
    the one that will use it.
    """
    value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Value"),
    )

    # Code generator:
    # ''.join(random.choices(string.ascii_uppercase.replace("O", "")
    #                           + string.digits.replace("0", ""), k=8))
    code = models.CharField(
        verbose_name=_("Code"),
        max_length=253,
    )

    start_time = models.DateTimeField(verbose_name=_("Start time"), )

    end_time = models.DateTimeField(verbose_name=_("End time"), )

    max_use = models.PositiveIntegerField()

    max_use_per_user = models.PositiveIntegerField()

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='coupons',
    )

    details = models.TextField(
        verbose_name=_("Details"),
        max_length=1000,
        null=True,
        blank=True,
    )

    applicable_retirements = models.ManyToManyField(
        'retirement.Retirement',
        related_name="applicable_coupons",
        verbose_name=_("Applicable retirements"),
        blank=True,
    )

    applicable_timeslots = models.ManyToManyField(
        'workplace.TimeSlot',
        related_name="applicable_coupons",
        verbose_name=_("Applicable timeslots"),
        blank=True,
    )

    applicable_packages = models.ManyToManyField(
        Package,
        related_name="applicable_coupons",
        verbose_name=_("Applicable packages"),
        blank=True,
    )

    applicable_memberships = models.ManyToManyField(
        Membership,
        related_name="applicable_coupons",
        verbose_name=_("Applicable memberships"),
        blank=True,
    )

    # This M2M field make a whole product family (ie: memberships) applicable
    # to a coupon. This overrides specific products.
    # For example, a coupon can be applied to "Membership 2", "Package 12" and
    # all "Retirement".
    applicable_product_types = models.ManyToManyField(
        ContentType,
        blank=True,
    )

    users = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Users"),
        related_name='used_coupons',
        through='CouponUser',
    )

    history = HistoricalRecords()

    def __str__(self):
        return self.code


class CouponUser(SafeDeleteModel):
    """Contains uses of coupons by users."""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='coupon_users',
    )
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.CASCADE,
        verbose_name=_("Coupon"),
        related_name='coupon_users',
    )
    uses = models.PositiveIntegerField()

    history = HistoricalRecords()

    def __str__(self):
        return ', '.join([str(self.coupon), str(self.user)])
