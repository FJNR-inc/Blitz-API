import decimal
import json
import random
import string
from decimal import Decimal

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation
)
from django.core.mail import send_mail
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string

from safedelete.models import SafeDeleteModel

from simple_history.models import HistoricalRecords

from blitz_api.models import AcademicLevel

from model_utils.managers import InheritanceManager

from log_management.models import Log, EmailLog

User = get_user_model()

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


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
            models.Q(content_type__model='retreat')
        )
        for orderline in orderlines:
            cost += orderline.cost
        return cost

    @property
    def total_cost_with_taxes(self):
        amount = self.total_cost * Decimal(repr(TAX_RATE + 1))
        return round(amount * 100, 2)

    @property
    def taxes(self):
        tax = self.total_cost * Decimal(repr(TAX_RATE))
        return tax.quantize(Decimal('0.01'))

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

    @staticmethod
    def send_invoice(to, merge_data):
        if 'POLICY_URL' not in merge_data.keys():
            merge_data['POLICY_URL'] = settings.\
                LOCAL_SETTINGS['FRONTEND_INTEGRATION']['POLICY_URL']

        plain_msg = render_to_string("invoice.txt", merge_data)
        msg_html = render_to_string("invoice.html", merge_data)

        try:
            response_send_mail = send_mail(
                "Confirmation d'achat",
                plain_msg,
                settings.DEFAULT_FROM_EMAIL,
                to,
                html_message=msg_html,
            )

            EmailLog.add(to, 'INVOICE', response_send_mail)
        except Exception as err:
            additional_data = {
                'title': "Confirmation d'achat",
                'default_from': settings.DEFAULT_FROM_EMAIL,
                'user_email': to,
                'merge_data': merge_data,
                'template': 'invoice'
            }
            Log.error(
                source='SENDING_BLUE_TEMPLATE',
                message=err,
                additional_data=json.dumps(additional_data)
            )
            raise

    def applying_coupon(self, coupon, user):
        from store.services import validate_coupon_for_order
        coupon_info = validate_coupon_for_order(coupon, self)
        if coupon_info['valid_use']:
            coupon_user = CouponUser.objects.get(
                user=user,
                coupon=coupon,
            )
            coupon_user.uses = coupon_user.uses + 1
            coupon_user.save()

            order_line: OrderLine = coupon_info['orderline']
            order_line.applying_coupon_value(coupon_info['value'])
            order_line.coupon = coupon
            order_line.save()

        return \
            coupon_info['valid_use'], \
            coupon_info['error'], \
            coupon_info['value']

    def add_line_from_data(self, orderlines_data):
        for orderline_data in orderlines_data:
            options_ids_quantity = orderline_data.pop('options', None)
            order_line: OrderLine = OrderLine.objects.create(
                order=self, **orderline_data)

            if options_ids_quantity:
                for option_id_quantity in options_ids_quantity:
                    option: BaseProduct = BaseProduct.objects.get(
                        id=option_id_quantity['id'])
                    quantity = option_id_quantity['quantity']
                    OrderLineBaseProduct.objects.create(
                        option=option,
                        order_line=order_line,
                        quantity=quantity
                    )
                    order_line.cost += option.price
                order_line.save()


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

    options = models.ManyToManyField(
        'BaseProduct',
        verbose_name=_("Options"),
        through='OrderLineBaseProduct',
        blank=True
    )

    metadata = models.TextField(
        verbose_name=_("Metada"),
        blank=True,
        null=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return str(self.content_object) + ', qt:' + str(self.quantity)

    def applying_coupon_value(self, coupon_value):
        self.cost = self.cost - coupon_value
        self.coupon_real_value = coupon_value
        self.save()

    def get_invitation(self):
        if self.metadata:
            metadata = json.loads(
                self.metadata)
            invitation_id = metadata.get(
                'invitation_id', None)

            if invitation_id:
                from retirement.models import RetreatInvitation
                return RetreatInvitation.objects.get(
                    id=invitation_id)
        return None


class OrderLineBaseProduct(models.Model):
    order_line = models.ForeignKey('OrderLine', on_delete=models.CASCADE)
    option = models.ForeignKey('BaseProduct', on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantity"),
    )


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

    refund_id = models.CharField(
        verbose_name=_("Refund ID"),
        max_length=253,
        null=True,
        blank=True,
    )

    history = HistoricalRecords()

    def __str__(self):
        return str(self.orderline) + ', ' + str(self.amount) + "$"


class BaseProduct(models.Model):
    objects = InheritanceManager()

    name = models.CharField(
        verbose_name=_("Name"),
        max_length=253,
    )

    available = models.BooleanField(
        verbose_name=_("Available"),
        default=False
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

    available_on_products = models.ManyToManyField(
        'self',
        verbose_name=_("Applicable products"),
        related_name='option_products',
        blank=True,
        symmetrical=False
    )

    available_on_product_types = models.ManyToManyField(
        ContentType,
        verbose_name=_("Applicable product types"),
        related_name='products',
        blank=True,
    )

    def __str__(self):
        return self.name

    def quantity_sold(self):
        return self.order_lines.count()

    @property
    def options(self):

        options_product_from_content_type = ContentType.objects. \
            get_for_model(self) \
            .products.exclude(id=self.id).select_subclasses()

        if options_product_from_content_type.count() > 0:
            return options_product_from_content_type
        else:
            return self.option_products.all().select_subclasses()


class Membership(BaseProduct):
    """Represents a membership."""

    class Meta:
        verbose_name = _("Membership")
        verbose_name_plural = _("Memberships")

    old_id = models.IntegerField(
        verbose_name=_("Id before migrate to base product"),
        null=True,
        blank=True
    )

    duration = models.DurationField()

    academic_levels = models.ManyToManyField(
        AcademicLevel,
        blank=True,
        verbose_name=_("Academic levels"),
        related_name='memberships',
    )

    # History is registered in translation.py
    # history = HistoricalRecords()


class Package(BaseProduct):
    """Represents a reservation package."""

    class Meta:
        verbose_name = _("Package")
        verbose_name_plural = _("Packages")

    old_id = models.IntegerField(
        verbose_name=_("Id before migrate to base product"),
        null=True,
        blank=True,
    )

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


class OptionProduct(BaseProduct):
    max_quantity = models.IntegerField(
        verbose_name=_("Max Quantity"),
        default=0
    )


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


class AbstractCoupon(SafeDeleteModel):
    """
    Common fields for Coupons and MembershipCoupons
    """

    # is zero if percent_off is not
    value = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        verbose_name=_("Value"),
        null=True,
        blank=True,
    )

    # is zero if value is not
    percent_off = models.PositiveIntegerField(
        verbose_name=_("Percentage off"),
        null=True,
        blank=True,
    )

    max_use = models.PositiveIntegerField()

    max_use_per_user = models.PositiveIntegerField()

    details = models.TextField(
        verbose_name=_("Details"),
        max_length=1000,
        null=True,
        blank=True,
    )

    applicable_retreats = models.ManyToManyField(
        'retirement.Retreat',
        related_name="applicable_%(class)ss",
        verbose_name=_("Applicable retreats"),
        blank=True,
    )

    applicable_timeslots = models.ManyToManyField(
        'workplace.TimeSlot',
        related_name="applicable_%(class)ss",
        verbose_name=_("Applicable timeslots"),
        blank=True,
    )

    applicable_packages = models.ManyToManyField(
        Package,
        related_name="applicable_%(class)ss",
        verbose_name=_("Applicable packages"),
        blank=True,
    )

    applicable_memberships = models.ManyToManyField(
        Membership,
        related_name="applicable_%(class)ss",
        verbose_name=_("Applicable memberships"),
        blank=True,
    )

    # This M2M field make a whole product family (ie: memberships) applicable
    # to a coupon. This overrides specific products.
    # For example, a coupon can be applied to "Membership 2", "Package 12" and
    # all "Retreat".
    applicable_product_types = models.ManyToManyField(
        ContentType,
        blank=True,
    )

    class Meta:
        abstract = True


class Coupon(AbstractCoupon):
    """
    Represents a coupon that provides a discount on various products.
    """

    start_time = models.DateTimeField(verbose_name=_("Start time"), )

    end_time = models.DateTimeField(verbose_name=_("End time"), )

    code = models.CharField(
        verbose_name=_("Code"),
        max_length=253,
    )

    #  The "owner" of the instance is the buyer of the coupon, but not
    #  necessarily the one that will use it.
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_("User"),
        related_name='coupons',
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

    def generate_code(self):
        self.code = ''.join(random.choices(
            string.ascii_uppercase.replace("O", "") +
            string.digits.replace("0", ""), k=8))


class MembershipCoupon(AbstractCoupon):
    """
    Represents a coupon that should be automatically generated when
    subscribing to a membership
    """

    # membership with which this coupon is given
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE)

    history = HistoricalRecords()


class CouponUser(SafeDeleteModel):
    """Contains uses of coupons by users."""

    class Meta:
        unique_together = (('user', 'coupon'),)

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
