from django.contrib.auth import get_user_model, password_validation
from django.conf import settings
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets, mixins
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, MethodNotAllowed

from imailing.Mailing import IMailing

from .models import (
    TemporaryToken, ActionToken, Domain, Organization, AcademicLevel,
    AcademicField,
)

from . import serializers, permissions

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
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
    Not implemented
    """
    queryset = User.objects.all()

    def get_serializer_class(self):
        if (self.action == 'update') | (self.action == 'partial_update'):
            return serializers.UserUpdateSerializer
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
        if self.action == 'create':
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
        raise MethodNotAllowed("DELETE")

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
        user = User.objects.get(email=request.data["email"])
        if response.status_code == status.HTTP_201_CREATED:
            if settings.LOCAL_SETTINGS['AUTO_ACTIVATE_USER'] is True:
                user.is_active = True
                user.save()

            if settings.LOCAL_SETTINGS['EMAIL_SERVICE'] is True:
                MAIL_SERVICE = settings.SETTINGS_IMAILING
                FRONTEND_SETTINGS = settings.LOCAL_SETTINGS[
                    'FRONTEND_INTEGRATION'
                ]

                # Get the token of the saved user and send it with an email
                activate_token = ActionToken.objects.get(
                    user=user,
                    type='account_activation',
                ).key

                # Setup the url for the activation button in the email
                activation_url = FRONTEND_SETTINGS['ACTIVATION_URL'].replace(
                    "{{token}}",
                    activate_token
                )

                # Send email with a SETTINGS_IMAILING
                email = IMailing.\
                    create_instance(MAIL_SERVICE["SERVICE"],
                                    MAIL_SERVICE["API_KEY"])
                response_send_mail = email.send_templated_email(
                    email_from=MAIL_SERVICE["EMAIL_FROM"],
                    template_id=MAIL_SERVICE["TEMPLATES"]["CONFIRM_SIGN_UP"],
                    list_to=[request.data["email"]],
                    context={
                        "activation_url": activation_url,
                        },
                )

                if response_send_mail["code"] == "failure":
                    content = {
                        'detail': _("The account was created but no email was "
                                    "sent. If your account is not "
                                    "activated, contact the administration."),
                    }
                    return Response(content, status=status.HTTP_201_CREATED)

        return response


class UsersActivation(APIView):
    """
    Activate user from an activation token
    """
    authentication_classes = ()
    permission_classes = ()

    def post(self, request):
        """
        Respond to POSTed email/password with token.
        """
        activation_token = request.data.get('activation_token')

        token = ActionToken.objects.filter(
            key=activation_token,
            type='account_activation',
        )

        # There is only one reference, we will set the user active
        if len(token) == 1:
            # We activate the user
            user = token[0].user
            user.is_active = True
            user.save()

            # We delete the token used
            token[0].delete()

            # We return the user
            serializer = serializers.UserSerializer(
                user,
                context={'request': request},
            )

            return Response(serializer.data)

        # There is no reference to this token or multiple identical token
        # token exists
        else:
            error = '"{0}" is not a valid activation_token.'. \
                format(activation_token)

            return Response(
                {'detail': error},
                status=status.HTTP_400_BAD_REQUEST
            )


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
        MAIL_SERVICE = settings.SETTINGS_IMAILING
        FRONTEND_SETTINGS = settings.LOCAL_SETTINGS['FRONTEND_INTEGRATION']

        button_url = FRONTEND_SETTINGS['FORGOT_PASSWORD_URL'].replace(
            "{{token}}",
            str(token)
        )

        email = IMailing.create_instance(
            MAIL_SERVICE["SERVICE"],
            MAIL_SERVICE["API_KEY"],
        )

        response_send_mail = email.send_templated_email(
            email_from=MAIL_SERVICE["EMAIL_FROM"],
            template_id=MAIL_SERVICE["TEMPLATES"]["FORGOT_PASSWORD"],
            list_to=[user.email],
            context={
                "forgot_password_url": button_url,
            },
        )

        if response_send_mail["code"] == "failure":
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


class OrganizationViewSet(viewsets.ModelViewSet):
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


class AcademicLevelViewSet(viewsets.ModelViewSet):
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


class AcademicFieldViewSet(viewsets.ModelViewSet):
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
