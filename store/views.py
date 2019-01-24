import pytz

from datetime import datetime

from django.conf import settings
from django.http import Http404, HttpResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from rest_framework import viewsets, status, mixins, exceptions
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, PaymentProfile,
                     CustomPayment, Coupon, Refund, )
from .permissions import IsOwner
from .resources import (MembershipResource, PackageResource, OrderResource,
                        OrderLineResource, CustomPaymentResource,
                        CouponResource, RefundResource, )
from .services import (delete_external_card, validate_coupon_for_order,
                       notify_for_coupon, )

from . import serializers, permissions


LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class MembershipViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given membership.

    list:
    Return a list of all the existing memberships.

    create:
    Create a new membership instance.
    """
    serializer_class = serializers.MembershipSerializer
    queryset = Membership.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filter_fields = {
        'duration': ['exact', 'gte', 'lte'],
        'academic_levels': ['exact', 'isnull'],
        'details': ['exact'],
        'available': ['exact'],
        'name': ['exact'],
        'price': ['exact', 'gte', 'lte'],
    }
    ordering = ('name',)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = MembershipResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Membership-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return available memberships except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Membership.objects.all()
        return Membership.objects.filter(available=True)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.available = False
            instance.save()
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class PackageViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given package.

    list:
    Return a list of all the existing packages.

    create:
    Create a new package instance.
    """
    serializer_class = serializers.PackageSerializer
    queryset = Package.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    filter_fields = {
        'reservations': ['exact', 'gte', 'lte'],
        'exclusive_memberships': ['exact', 'isnull'],
        'details': ['exact'],
        'available': ['exact'],
        'name': ['exact'],
        'price': ['exact', 'gte', 'lte'],
    }
    ordering = ('name',)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = PackageResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Package-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return available memberships except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Package.objects.all()
        return Package.objects.filter(available=True)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.available = False
            instance.save()
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class PaymentProfileViewSet(
        viewsets.GenericViewSet,
        mixins.ListModelMixin,
        mixins.RetrieveModelMixin):
    """
    retrieve:
    Return the given payment profile.

    list:
    Return a list of all the existing payment profiles.
    """
    serializer_class = serializers.PaymentProfileSerializer
    queryset = PaymentProfile.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, IsAuthenticated)
    filter_fields = '__all__'

    def cards(self, request, *args, **kwargs):
        """
        This custom action is manually routed in urls.py
        """
        payment_profile = self.get_object()
        card_id = kwargs['card_id']
        try:
            delete_external_card(
                payment_profile.external_api_id,
                card_id,
            )
        except PaymentAPIError as err:
            return Response(
                {'message': str(err)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """
        This viewset should return a user's credit cards except if the
        currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return PaymentProfile.objects.all()
        return PaymentProfile.objects.filter(owner=self.request.user)


class OrderViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given order.

    list:
    Return a list of all the existing orders.

    create:
    Create a new order instance.
    """
    serializer_class = serializers.OrderSerializer
    queryset = Order.objects.all()
    permission_classes = (permissions.IsAdminOrCreateReadOnly, IsAuthenticated)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = OrderResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Order-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    @action(
        methods=['post'], detail=False, permission_classes=[IsAuthenticated])
    def validate_coupon(self, request, pk=None):
        """
        This validates if a coupon can be used in an order.
        It has to create temporary objects to be able to use querysets.
        Temporary objects are then deleted.

        This is not the best way to do it and it could be improved.
        """
        serializer = serializers.OrderSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        # Coupon is necessary for this view
        if not serializer.validated_data.get('coupon'):
            error = {
                'coupon': [_("This field is required.")]
            }
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
        orderlines = serializer.validated_data.pop('order_lines', None)
        coupon = serializer.validated_data.pop('coupon', None)
        serializer.validated_data.pop('payment_token', None)
        serializer.validated_data.pop('single_use_token', None)
        order = Order(
            **serializer.validated_data,
            transaction_date=timezone.now(),
            user=request.user,
        )
        order.save()

        orderline_list = []
        for idx, orderline in enumerate(orderlines):
            orderline_list.append(
                OrderLine(
                    **orderline,
                    order=order,
                )
            )
            orderline_list[idx].save()

        response = validate_coupon_for_order(coupon, order)
        response['orderline'] = serializers.OrderLineSerializerNoOrder(
            response['orderline'],
            context={'request': request}
        ).data
        response['orderline'].pop('url', None)
        response['orderline'].pop('id', None)
        response['orderline'].pop('order', None)
        response['orderline'].pop('coupon', None)
        response['orderline'].pop('coupon_real_value', None)
        response['orderline'].pop('cost', None)
        order.delete()
        for orderline in orderline_list:
            orderline.delete()
        if response['valid_use']:
            response.pop('valid_use', None)
            response.pop('error', None)
            return Response(response)
        return Response(response['error'], status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        """
        This viewset should return owned orders except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user.id)


class OrderLineViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given order line.

    list:
    Return a list of all the existing order lines.

    create:
    Create a new order line instance.
    """
    serializer_class = serializers.OrderLineSerializer
    queryset = OrderLine.objects.all()
    permission_classes = (IsAuthenticated,)

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = OrderLineResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="OrderLine-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return owned order lines except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return OrderLine.objects.all()
        return OrderLine.objects.filter(order__user=self.request.user)


class CustomPaymentViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given custom payment.

    list:
    Return a list of all the existing custom payments.

    create:
    Create a new custom payment instance.
    """
    serializer_class = serializers.CustomPaymentSerializer
    queryset = CustomPayment.objects.all()
    permission_classes = (IsAuthenticated, permissions.IsAdminOrReadOnly)
    filter_fields = '__all__'

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = CustomPaymentResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="CustomPayment-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return owned custom payments except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return CustomPayment.objects.all()
        return CustomPayment.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class CouponViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given coupon.

    list:
    Return a list of all the existing coupons.

    create:
    Create a new coupon instance.
    """
    serializer_class = serializers.CouponSerializer
    queryset = Coupon.objects.all()
    permission_classes = (IsAuthenticated, permissions.IsAdminOrReadOnly)
    filter_fields = '__all__'

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = CouponResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Coupon-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    @action(methods=['post'], detail=True, permission_classes=[IsOwner])
    def notify(self, request, pk=None):
        """
        That custom action allows a coupon owner to notify users with the
        coupon code.

        We're using a DRF serializer field on-the-fly here to validate the
        email list.
        """
        email_list_data = request.data.get('email_list', None)

        serializer = drf_serializers.ListField(
            child=drf_serializers.EmailField(
                label=_('Email address'),
                max_length=254,
                required=True,
            )
        )

        if not email_list_data:
            raise exceptions.ValidationError({
                "email_list": _("This field is required.")
            })
        try:
            email_list = serializer.to_internal_value(email_list_data)
        except exceptions.ValidationError as err:
            if isinstance(err.detail, dict):
                if err.detail.get(0):
                    raise exceptions.ValidationError({
                        "email_list": [str(msg) for msg in err.detail.get(0)]
                    })
            raise exceptions.ValidationError({
                "email_list": [str(msg) for msg in err.detail]
            })

        for email in email_list:
            # Notify every user in the list
            notify_for_coupon(
                email,
                self.get_object(),
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        """
        This viewset should return owned coupons except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return Coupon.objects.all()
        return Coupon.objects.filter(owner=self.request.user)

    def destroy(self, request, *args, **kwargs):
        try:
            super(CouponViewSet, self).destroy(request, *args, **kwargs)
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class RefundViewSet(viewsets.GenericViewSet,
                    mixins.ListModelMixin,
                    mixins.RetrieveModelMixin, ):
    """
    retrieve:
    Return the given refund.

    list:
    Return a list of all the existing refunds.
    """
    serializer_class = serializers.RefundSerializer
    queryset = Refund.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly, IsAuthenticated)
    filter_fields = '__all__'

    @action(detail=False, permission_classes=[IsAdminUser])
    def export(self, request):
        dataset = RefundResource().export()
        response = HttpResponse(
            dataset.xls,
            content_type="application/vnd.ms-excel"
        )
        response['Content-Disposition'] = ''.join([
            'attachment; filename="Refund-',
            LOCAL_TIMEZONE.localize(datetime.now()).strftime("%Y%m%d-%H%M%S"),
            '".xls'
        ])
        return response

    def get_queryset(self):
        """
        This viewset should return a user's refunds except if he's admin.
        """
        if self.request.user.is_staff:
            return Refund.objects.all()
        return Refund.objects.filter(
            orderline__order__user=self.request.user
        )
