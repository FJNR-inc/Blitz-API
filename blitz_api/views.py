from django.contrib.auth import (get_user_model,
                                 authenticate,
                                 password_validation)
from django.conf import settings
from django.utils import timezone
from django.http import Http404
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from imailing.Mailing import IMailing

from .models import TemporaryToken, ActionToken, Domain, Organization

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
    """
    serializer_class = serializers.UserSerializer
    queryset = User.objects.all()

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
        user = User.objects.get(username=request.data["username"])
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
        Respond to POSTed username/password with token.
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

        # There is no reference to this token
        elif not token:
            error = '"{0}" is not a valid activation_token.'. \
                format(activation_token)

            return Response(
                {'detail': error},
                status=status.HTTP_400_BAD_REQUEST
            )
        # We have multiple token with the same key (impossible)
        else:
            error = _("The system have a problem, please contact us, "
                      "it is not your fault.")
            return Response(
                {'detail': error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ObtainTemporaryAuthToken(ObtainAuthToken):
    """
    Enables username/password exchange for expiring token.
    """
    model = TemporaryToken

    def post(self, request):
        """
        Respond to POSTed username/password with token.
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

        if token and token.expired:
            # If the token is expired, generate a new one.
            token.delete()
            expires = timezone.now() + timezone.timedelta(
                minutes=CONFIG['MINUTES']
            )

            token = TemporaryToken.objects.create(
                user=user, expires=expires)

        if token:
            data = {'token': token.key}
            return Response(data)

        error = _("Could not authenticate user.")
        return Response(
            {'error': error},
            status=status.HTTP_400_BAD_REQUEST
        )


