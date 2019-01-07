import pytz

from datetime import datetime

from django.conf import settings
from django.http import Http404, HttpResponse

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from .exceptions import PaymentAPIError
from .models import (Package, Membership, Order, OrderLine, PaymentProfile,
                     CustomPayment, Coupon, )
from .resources import (MembershipResource, PackageResource, OrderResource,
                        OrderLineResource, CustomPaymentResource,
                        CouponResource, )
from .services import delete_external_card

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
