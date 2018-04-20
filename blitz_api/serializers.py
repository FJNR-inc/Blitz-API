from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate, password_validation

User = get_user_model()


class AuthCustomTokenSerializer(serializers.Serializer):
    """
    Verifies if the provided login is an email or username
    """
    login = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        login = attrs.get('login')
        password = attrs.get('password')

        if login and password:
            try:
                user_obj = User.objects.get(email=login)
                if user_obj:
                    login = user_obj.username
            except User.DoesNotExist:
                pass

            user = authenticate(request=self.context.get('request'),
                                username=login, password=password)

            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg)
        else:
            msg = _('Must include "login" and "password".')
            raise serializers.ValidationError(msg)

        attrs['user'] = user

        return attrs
