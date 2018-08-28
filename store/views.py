from django.http import Http404

from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (Package, Membership, Order, OrderLine, PaymentProfile,)

from . import serializers, permissions


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

    def get_queryset(self):
        """
        This viewset should return owned order lines except if
        the currently authenticated user is an admin (is_staff).
        """
        if self.request.user.is_staff:
            return OrderLine.objects.all()
        return OrderLine.objects.filter(order__user=self.request.user)
