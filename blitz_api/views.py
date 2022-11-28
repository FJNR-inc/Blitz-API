import base64
import json

import pytz

from datetime import datetime

from django.contrib.auth import get_user_model, password_validation
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.http import Http404, HttpResponse
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets, mixins, filters, generics
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from blitz_api.mixins import ExportMixin
from log_management.models import EmailLog
from .models import (
    TemporaryToken, ActionToken, Domain, Organization, AcademicLevel,
    AcademicField,
    ExportMedia)
from .resources import (AcademicFieldResource, AcademicLevelResource,
                        OrganizationResource, UserResource)
from . import serializers, permissions, services
from store.permissions import IsOwner
from store.models import Order
from store.serializers import OrderHistorySerializer

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class UserViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given user.

    list:
    Return a list of all the existing users.

    create:
    Create a new user instance.

    update:
    Update fields of a user instance.

    delete:
    Sets the user inactive.
    """
    queryset = User.objects.all()
    filterset_fields = {
        'email',
        'phone',
        'other_phone',
        'academic_field',
        'university',
        'academic_level',
        'membership',
        'last_login',
        'first_name',
        'last_name',
        'is_active',
        'date_joined',
        'birthdate',
        'gender',
        'membership_end',
        'tickets',
        'groups',
        'user_permissions',
    }
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('email',)

    export_resource = UserResource()

    def get_serializer_class(self):
        if (self.action == 'update') | (self.action == 'partial_update'):
            return serializers.UserUpdateSerializer
        elif self.action == 'order_history':
            return OrderHistorySerializer
        return serializers.UserSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = User.objects.all()
        if self.kwargs.get("pk", "") == "me":
            self.kwargs['pk'] = user.id
        return queryset

    def get_permissions(self):
        """
        Returns the list of permissions that this view requires.
        """
        if self.action in [
            'create',
            'resend_activation_email',
            'execute_automatic_email_membership_end'
        ]:
            permission_classes = []
        elif self.action == 'list':
            permission_classes = [IsAdminUser, ]
        else:
            permission_classes = [
                IsAuthenticated,
                permissions.IsOwner
            ]
        return [permission() for permission in permission_classes]

    def retrieve(self, request, *args, **kwargs):
        """ Hides non-existent objects by denying permission """
        if request.user.is_staff:
            return super().retrieve(request, *args, **kwargs)
        try:
            return super().retrieve(request, *args, **kwargs)
        except Http404:
            raise PermissionDenied

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.is_active = False
            instance.save()
        except Http404:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        """ Hides non-existent objects by denying permission """
        if request.user.is_staff:
            return super().update(request, *args, **kwargs)
        try:
            return super().update(request, *args, **kwargs)
        except Http404:
            raise PermissionDenied

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email=request.data["email"].strip())

            if settings.LOCAL_SETTINGS['AUTO_ACTIVATE_USER'] is True:
                user.is_active = True
                user.save()

            user.send_new_activation_email()

        return response

    @action(detail=True, permission_classes=[IsAdminUser])
    def send_email_confirm(self, request, pk):
        user = self.get_object()
        user.send_new_activation_email()

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[])
    def execute_automatic_email_membership_end(self, request):
        """
        That custom action allows an admin (or an automated task) to
        notify a users that his membership comes to an end
        """

        emails = []
        for user in User.objects.all():
            email_send = user.check_and_notify_renew_membership()

            if email_send:
                emails.append(user.email)

        response_data = {
            'stop': False,
            'email_send_count': len(emails)
        }
        return Response(response_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'], permission_classes=[])
    def resend_activation_email(self, request):
        """
        That custom action allows an user to trigger a new email of activation
        in case the first email was not received or was received too long ago
        """

        serializer = serializers.ResendEmailActivationSerializer(
            data=self.request.data,
            context={
                'request': request,
            }
        )

        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=serializer.validated_data['email'])
            user.send_new_activation_email()
        except User.DoesNotExist:
            return Response(
                {
                    'email': _('This email is not linked to any account'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def accept_terms(self, request, pk):
        user = self.get_object()

        is_owner = user.id == self.request.user.id
        is_admin = self.request.user.is_superuser

        if is_owner or is_admin:
            user.last_acceptation_terms_and_conditions = timezone.now()
            user.save()
        else:
            content = {
                'non_field_errors': _(
                    "You can't accept the terms for others peoples."
                ),
            }
            return Response(content, status=status.HTTP_403_FORBIDDEN)

        return Response(status=status.HTTP_200_OK)

    @action(detail=True, permission_classes=[IsOwner])
    def order_history(self, request, pk=None):
        user = self.get_object()
        orders = Order.objects.filter(user=user)
        response = self.get_serializer(orders, many=True).data
        return Response(
            status=status.HTTP_200_OK,
            data=response
        )


class UsersActivation(APIView):
    """
    Activate email from an activation token or email change token
    """
    authentication_classes = ()
    permission_classes = ()

    def post(self, request):
        """
        Activate email if the provided Token is valid.
        """
        activation_token = request.data.get('activation_token')

        new_account_token = ActionToken.objects.filter(
            key=activation_token,
            type='account_activation',
        )
        change_email_token = ActionToken.objects.filter(
            key=activation_token,
            type='email_change',
        )

        # There is no reference to this token or multiple identical token
        # exists.
        if ((not new_account_token and not change_email_token)
                or (new_account_token.count() > 1
                    and change_email_token.count() > 1)):
            error = '"{0}" is not a valid activation_token.'. \
                format(activation_token)

            return Response(
                {'detail': error},
                status=status.HTTP_400_BAD_REQUEST
            )

        # There is only one reference, we will set the user active
        if len(new_account_token) == 1:
            # We activate the user
            user = new_account_token[0].user
            user.is_active = True
            user.save()

            # We delete the token used
            new_account_token[0].delete()

            # Authenticate the user automatically
            token, _created = TemporaryToken.objects.get_or_create(
                user=user
            )
            CONFIG = settings.REST_FRAMEWORK_TEMPORARY_TOKENS
            token.expires = timezone.now() + timezone.timedelta(
                minutes=CONFIG['MINUTES']
            )
            token.save()

            # We return the user
            serializer = serializers.UserSerializer(
                user,
                context={'request': request},
            )

            return_data = dict()
            return_data['user'] = serializer.data
            return_data['token'] = token.key

            return Response(return_data)

        # There is only one reference, we will change user's informations
        # The ActionToken's data field can include 'email' and 'university_id'
        # fields.
        # NOTE: This assumes that data validation was done before creating the
        # activation token and submitting it here.
        if len(change_email_token) == 1:
            # We activate the user
            user = change_email_token[0].user
            new_email = change_email_token[0].data.get('email', None)
            new_university_id = change_email_token[0].data.get(
                'university_id', None
            )
            # If no email is provided in the ActionToken's data field, this is
            # considered to be a bug.
            if not new_email:
                error = '"{0}" is not a valid activation_token.'. \
                    format(activation_token)

                return Response(
                    {'detail': error},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if User.objects.filter(username=new_email).exists():
                error = 'An account with the same email already exist.'

                return Response(
                    {'detail': error},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update user info
            user.email = new_email
            user.username = new_email
            if new_university_id:
                user.university = Organization.objects.get(
                    pk=new_university_id
                )
            else:
                user.university = None
            user.save()

            # We delete the token used
            change_email_token[0].delete()

            # Authenticate the user automatically
            token, _created = TemporaryToken.objects.get_or_create(
                user=user
            )
            CONFIG = settings.REST_FRAMEWORK_TEMPORARY_TOKENS
            token.expires = timezone.now() + timezone.timedelta(
                minutes=CONFIG['MINUTES']
            )
            token.save()

            # We return the user
            serializer = serializers.UserSerializer(
                user,
                context={'request': request},
            )

            return_data = dict()
            return_data['user'] = serializer.data
            return_data['token'] = token.key

            return Response(return_data)


class ResetPassword(APIView):
    """
    post:
    Create a new token allowing user to change his password.
    """
    permission_classes = ()
    authentication_classes = ()

    def post(self, request, *args, **kwargs):
        if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is not True:
            # Without email this functionality is not provided
            return Response(status=status.HTTP_501_NOT_IMPLEMENTED)

        # Valid params
        serializer = serializers.ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        # remove old tokens to change password
        tokens = ActionToken.objects.filter(
            type='password_change',
            user=user,
        )

        for token in tokens:
            token.expire()

        # create the new token
        token = ActionToken.objects.create(
            type='password_change',
            user=user,
        )

        # Send the new token by e-mail to the user
        MAIL_SERVICE = settings.ANYMAIL
        FRONTEND_SETTINGS = settings.LOCAL_SETTINGS['FRONTEND_INTEGRATION']

        button_url = FRONTEND_SETTINGS['FORGOT_PASSWORD_URL'].replace(
            "{{token}}",
            str(token)
        )

        response_send_mail = services.send_mail(
            [user],
            {"forgot_password_url": button_url},
            "FORGOT_PASSWORD",
        )

        if response_send_mail:
            content = {
                'detail': _("Your token has been created but no email "
                            "has been sent. Please contact the "
                            "administration."),
            }
            return Response(content, status=status.HTTP_201_CREATED)

        else:
            return Response(status=status.HTTP_201_CREATED)


class ChangePassword(APIView):
    """
    post:
    Get a token and a new password and change the password of
    the token's owner.
    """
    authentication_classes = ()
    permission_classes = ()
    serializer_class = serializers.UserSerializer

    def post(self, request):
        # Valid params
        serializer = serializers.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = request.data.get('token')
        new_password = request.data.get('new_password')

        tokens = ActionToken.objects.filter(
            key=token,
            type='password_change',
            expired=False,
        )

        # There is only one reference, we will change the user password
        if len(tokens) == 1:
            user = tokens[0].user
            try:
                password_validation.validate_password(password=new_password)
            except ValidationError as err:
                content = {
                    'detail': err,
                }
                return Response(content, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            # We expire the token used
            tokens[0].expire()

            # We return the user
            serializer = serializers.UserSerializer(
                user,
                context={'request': request}
            )

            return Response(serializer.data)

        # There is no reference to this token or multiple identical token
        # token exists
        else:
            error = '{0} is not a valid token.'.format(token)

            return Response(
                {'detail': error},
                status=status.HTTP_400_BAD_REQUEST
            )


class DomainViewSet(viewsets.ModelViewSet):
    """
    retrieve:
    Return the given domain.

    list:
    Return a list of all the existing domains.

    create:
    Create a new domain instance.
    """
    serializer_class = serializers.DomainSerializer
    queryset = Domain.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    ordering = ('name',)


class OrganizationViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given organization.

    list:
    Return a list of all the existing organizations.

    create:
    Create a new organization instance.
    """
    serializer_class = serializers.OrganizationSerializer
    queryset = Organization.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    ordering = ('name',)

    export_resource = OrganizationResource()


class ObtainTemporaryAuthToken(ObtainAuthToken):
    """
    Enables email/password exchange for expiring token.
    """
    model = TemporaryToken

    def post(self, request):
        """
        Respond to POSTed email/password with token.
        """
        CONFIG = settings.REST_FRAMEWORK_TEMPORARY_TOKENS
        serializer = serializers.CustomAuthTokenSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token = None

        token, _created = TemporaryToken.objects.get_or_create(
            user=user
        )

        if token.expired:
            # If the token is expired, generate a new one.
            token.delete()
            expires = timezone.now() + timezone.timedelta(
                minutes=CONFIG['MINUTES']
            )

            token = TemporaryToken.objects.create(
                user=user, expires=expires)

        data = {'token': token.key}
        return Response(data)


class TemporaryTokenDestroy(viewsets.GenericViewSet, mixins.DestroyModelMixin):
    """
    destroy:
    Delete a TemporaryToken object. Used to logout.
    """
    queryset = TemporaryToken.objects.none()

    def get_queryset(self):
        key = self.kwargs.get('pk')
        tokens = TemporaryToken.objects.filter(
            key=key,
            user=self.request.user,
        )
        return tokens


class AcademicLevelViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given academic level.

    list:
    Return a list of all the existing academic levels.

    create:
    Create a new academic level instance.
    """
    serializer_class = serializers.AcademicLevelSerializer
    queryset = AcademicLevel.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    ordering = ('name',)

    export_resource = AcademicLevelResource()


class AcademicFieldViewSet(ExportMixin, viewsets.ModelViewSet):
    """
    retrieve:
    Return the given academic field.

    list:
    Return a list of all the existing academic fields.

    create:
    Create a new academic field instance.
    """
    serializer_class = serializers.AcademicFieldSerializer
    queryset = AcademicField.objects.all()
    permission_classes = (permissions.IsAdminOrReadOnly,)
    ordering = ('name',)

    export_resource = AcademicFieldResource()


class ExportMediaViewSet(viewsets.ModelViewSet):
    parser_classes = (MultiPartParser,)
    serializer_class = serializers.ExportMediaSerializer
    queryset = ExportMedia.objects.all()
    permission_classes = (IsAdminUser,)


class MailChimpView(generics.CreateAPIView):
    serializer_class = serializers.MailChimpSerializer
    permission_classes = []
