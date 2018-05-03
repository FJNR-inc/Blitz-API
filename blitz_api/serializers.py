import re
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from .models import Domain, Organization, ActionToken

User = get_user_model()


class AuthCustomTokenSerializer(serializers.Serializer):
# Validator for phone numbers
def phone_number_validator(phone):
    reg = re.compile('^([+][0-9]{1,2})?[0-9]{9,10}$')
    char_list = " -.()"
    for i in char_list:
        phone = phone.replace(i, '')
    if not reg.match(phone):
        raise serializers.ValidationError(_("Invalid format."))
    return phone


class UserSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    new_password = serializers.CharField(max_length=128, required=False)
    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message=_(
                    "An account for the specified email "
                    "address already exists."
                ),
            ),
        ],
    )
    phone = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        label=_('Phone number'),
        max_length=17,
        required=False,
    )
    other_phone = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        label=_('Other number'),
        max_length=17,
        required=False,
    )
    university = OrganizationSerializer()

    def validate_university(self, value):
        """
        Check that the university exists.
        """
        org = Organization.objects.filter(name=value['name'])

        if org:
            return org[0]
        raise serializers.ValidationError(_("This university does not exist."))

    def validate_phone(self, value):
        return phone_number_validator(value)

    def validate_other_phone(self, value):
        return phone_number_validator(value)

    def validate_password(self, value):
        try:
            password_validation.validate_password(password=value)
        except ValidationError as err:
            raise serializers.ValidationError(err.messages)
        return value

    def validate_new_password(self, value):
        try:
            password_validation.validate_password(password=value)
        except ValidationError as err:
            raise serializers.ValidationError(err.messages)
        return value

    def create(self, validated_data):
        """
        Check that the email domain correspond to the university.
        """
        try:
            domains = Organization.objects.get(
                name=validated_data['university'].name
            ).domains.all()
        except Organization.DoesNotExist:
            raise serializers.ValidationError(
                _("This university does not exist.")
            )

        email_domain = validated_data['email'].split("@", 1)[1]
        if not any(d.name == email_domain for d in domains):
            raise serializers.ValidationError(_("Invalid domain name."))

        user = User(**validated_data)

        # Hash the user's password
        user.set_password(validated_data['password'])

        # Put user inactive by default
        user.is_active = False

        user.save()

        # Create an ActivationToken to activate user in the future
        ActionToken.objects.create(
            user=user,
            type='account_activation',
        )

        return user

    def update(self, instance, validated_data):
        # Drop keys that cannot be updated. None ensures that no exception is
        # raised if the key doesn't exist.
        validated_data.pop("university", None)
        validated_data.pop("email", None)
        validated_data.pop("academic_level", None)
        if 'new_password' in validated_data.keys():
            try:
                old_pw = validated_data.pop('password')
            except KeyError:
                raise serializers.ValidationError(
                    _("This field is required.")
                )

            new_pw = validated_data.pop('new_password')

            if instance.check_password(old_pw):
                instance.set_password(new_pw)
            else:
                msg = _("Bad password.")
                raise serializers.ValidationError(msg)

        return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
            'new_password': {'write_only': True},
            'university': {'required': True},
        }
        read_only_fields = (
            'id',
            'url',
            'is_staff',
            'is_superuser',
            'is_active',
            'date_joined',
            'last_login',
            'groups',
            'user_permissions',
        )


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
