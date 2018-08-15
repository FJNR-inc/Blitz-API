import re
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.compat import authenticate
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models.base import ObjectDoesNotExist

from .models import (
    Domain, Organization, ActionToken, AcademicField, AcademicLevel,
)
from store.serializers import MembershipSerializer

User = get_user_model()


# Validator for phone numbers
def phone_number_validator(phone):
    reg = re.compile('^([+][0-9]{1,2})?[0-9]{9,10}$')
    char_list = " -.()"
    for i in char_list:
        phone = phone.replace(i, '')
    if not reg.match(phone):
        raise serializers.ValidationError(_("Invalid format."))
    return phone


class DomainSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Domain
        fields = '__all__'


class OrganizationSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        max_length=100,
        required=True,
    )
    domains = DomainSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = '__all__'


class AcademicLevelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        max_length=100,
        required=True,
    )

    class Meta:
        model = AcademicLevel
        fields = '__all__'


class AcademicFieldSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        max_length=100,
        required=True,
    )

    class Meta:
        model = AcademicField
        fields = '__all__'


class UserUpdateSerializer(serializers.HyperlinkedModelSerializer):
    """
    Set  certain fields such as university, academic_level and email to read
    only.
    """
    id = serializers.ReadOnlyField()
    username = serializers.HiddenField(default=None)
    new_password = serializers.CharField(max_length=128, required=False)
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
    academic_field = AcademicFieldSerializer()
    university = OrganizationSerializer(read_only=True)
    academic_level = AcademicLevelSerializer(read_only=True)
    membership = MembershipSerializer(
        read_only=True,
    )

    def validate_academic_field(self, value):
        """
        Check that the academic field exists.
        """
        if 'name' in value:
            field = AcademicField.objects.filter(name=value['name'])

            if field:
                return field[0]
        raise serializers.ValidationError(
            _("This academic field does not exist.")
        )

    def validate_phone(self, value):
        return phone_number_validator(value)

    def validate_other_phone(self, value):
        return phone_number_validator(value)

    def update(self, instance, validated_data):
        validated_data['username'] = instance.username
        if 'new_password' in validated_data.keys():
            try:
                old_pw = validated_data.pop('password')
            except KeyError:
                raise serializers.ValidationError({
                    'password': _("This field is required.")
                })

            new_pw = validated_data.pop('new_password')

            try:
                password_validation.validate_password(password=new_pw)
            except ValidationError as err:
                raise serializers.ValidationError({
                    'new_password': err.messages
                })

            if instance.check_password(old_pw):
                instance.set_password(new_pw)
                instance.save()
            else:
                msg = {'password': _("Bad password")}
                raise serializers.ValidationError(msg)

        return super().update(instance, validated_data)

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
            'new_password': {'write_only': True},
            'gender': {
                'allow_blank': False,
            },
            'first_name': {
                'allow_blank': False,
            },
            'last_name': {
                'allow_blank': False,
            },
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
            'university',
            'academic_level',
            'email',
            'reservations',
        )


class UserSerializer(UserUpdateSerializer):
    """
    Complete serializer for user creation
    """
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
    university = OrganizationSerializer(required=False)
    academic_level = AcademicLevelSerializer(required=False)
    academic_field = AcademicFieldSerializer(required=False)
    membership = MembershipSerializer(
        read_only=True,
    )

    def validate_university(self, value):
        """
        Check that the university exists.
        """
        if 'name' in value:
            org = Organization.objects.filter(name=value['name'])

            if org:
                return org[0]
        raise serializers.ValidationError(_("This university does not exist."))

    def validate_academic_level(self, value):
        """
        Check that the academic level exists.
        """
        if 'name' in value:
            lvl = AcademicLevel.objects.filter(name=value['name'])

            if lvl:
                return lvl[0]
        raise serializers.ValidationError(
            _("This academic level does not exist.")
        )

    def validate_password(self, value):
        try:
            password_validation.validate_password(password=value)
        except ValidationError as err:
            raise serializers.ValidationError(err.messages)
        return value

    def validate(self, attrs):
        content = {}
        if 'email' in attrs:
            attrs['username'] = attrs['email']
        if 'university' in attrs:
            for key in ['academic_level', 'academic_field']:
                if key not in attrs:
                    content[key] = [_('This field is required.')]

        if content:
            raise serializers.ValidationError(content)

        return attrs

    def create(self, validated_data):
        """
        Check that the email domain correspond to the university.
        """
        if 'university' in validated_data:
            domains = Organization.objects.get(
                name=validated_data['university'].name
            ).domains.all()

            email_domain = validated_data['email'].split("@", 1)[1]
            if not any(d.name == email_domain for d in domains):
                raise serializers.ValidationError({
                    'email': [_("Invalid domain name.")]
                })

        user = User(**validated_data)

        # Hash the user's password
        user.set_password(validated_data['password'])

        # Put user inactive by default
        user.is_active = False

        # Free ticket for new users
        user.tickets = 1

        user.save()

        # Create an ActivationToken to activate user in the future
        ActionToken.objects.create(
            user=user,
            type='account_activation',
        )

        return user

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True},
            'new_password': {'write_only': True},
            'gender': {
                'required': True,
                'allow_blank': False,
            },
            'first_name': {
                'required': True,
                'allow_blank': False,
            },
            'last_name': {
                'required': True,
                'allow_blank': False,
            },
            'birthdate': {
                'required': True,
            },
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
            'reservations',
        )


class CustomAuthTokenSerializer(AuthTokenSerializer):
    """
    Subclass of default AuthTokenSerializer to enable email authentication
    """
    username = serializers.CharField(label=_("Username"), required=True)
    password = serializers.CharField(
        label=_("Password"),
        style={'input_type': 'password'},
        trim_whitespace=False,
        required=True,
    )

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        try:
            user_obj = User.objects.get(email=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass

        user = authenticate(request=self.context.get('request'),
                            username=username, password=password)

        if not user:
            msg = _('Unable to log in with provided credentials.')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user

        return attrs


class ResetPasswordSerializer(serializers.Serializer):

    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,
    )

    def validate_email(self, value):
        if User.objects.filter(email=value):
            return value
        raise serializers.ValidationError(
            _("No account associated to this email address.")
        )

    def validate(self, attrs):
        return User.objects.get(email=attrs['email'])


class ChangePasswordSerializer(serializers.Serializer):

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
