import re

from django.db.models import Q
from django.utils import timezone
from mailchimp3.mailchimpclient import MailChimpError
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from django.contrib.auth import (get_user_model, password_validation,
                                 authenticate, )
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import (
    Domain, Organization, ActionToken, AcademicField, AcademicLevel,
    ExportMedia
)
from .services import remove_translation_fields, check_if_translated_field
from . import services, mailchimp
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
        required=False,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
    )
    domains = DomainSerializer(many=True, read_only=True)

    def validate(self, attr):
        if not check_if_translated_field('name', attr):
            raise serializers.ValidationError({
                'name': _("This field is required.")
            })
        return super(OrganizationSerializer, self).validate(attr)

    def to_representation(self, instance):
        data = super(OrganizationSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = Organization
        fields = '__all__'


class AcademicLevelSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        max_length=100,
        required=False,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
    )

    def validate(self, attr):
        if not check_if_translated_field('name', attr):
            raise serializers.ValidationError({
                'name': _("This field is required.")
            })
        return super(AcademicLevelSerializer, self).validate(attr)

    def to_representation(self, instance):
        data = super(AcademicLevelSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = AcademicLevel
        fields = '__all__'


class AcademicFieldSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    name = serializers.CharField(
        max_length=100,
        required=False,
    )
    name_fr = serializers.CharField(
        required=False,
        allow_null=True,
    )
    name_en = serializers.CharField(
        required=False,
        allow_null=True,
    )

    def validate(self, attr):
        if not check_if_translated_field('name', attr):
            raise serializers.ValidationError({
                'name': _("This field is required.")
            })
        return super(AcademicFieldSerializer, self).validate(attr)

    def to_representation(self, instance):
        data = super(AcademicFieldSerializer, self).to_representation(instance)
        if self.context['request'].user.is_staff:
            return data
        return remove_translation_fields(data)

    class Meta:
        model = AcademicField
        fields = '__all__'


class UserUpdateSerializer(serializers.HyperlinkedModelSerializer):
    """
    Set  certain fields such as university and email to read
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
    university = OrganizationSerializer(
        allow_null=True,
    )
    academic_level = AcademicLevelSerializer()
    membership = MembershipSerializer(
        read_only=True,
    )
    volunteer_for_workplace = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='workplace-detail',
        source='workplaces',
    )
    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,
    )
    is_in_newsletter = serializers.ReadOnlyField()
    get_number_of_past_tomatoes = serializers.ReadOnlyField()
    get_number_of_future_tomatoes = serializers.ReadOnlyField()

    def validate_email(self, value):
        """
        Lowercase all email addresses.
        """
        if User.objects.filter(email__iexact=value):
            if self.context['request'].user.email != value:
                raise serializers.ValidationError(_(
                    "An account for the specified email "
                    "address already exists."
                ))
        return value

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

    def validate_academic_level(self, value):
        """
        Check that the academic level exists.
        """
        if 'name' in value:
            field = AcademicLevel.objects.filter(name=value['name'])

            if field:
                return field[0]
        raise serializers.ValidationError(
            _("This academic level does not exist.")
        )

    def validate_university(self, value):
        """
        Check that the university exists.
        """
        if not value:
            return value
        if 'name' in value:
            org = Organization.objects.filter(name=value['name'])

            if org:
                return org[0]
        raise serializers.ValidationError(_("This university does not exist."))

    def validate_phone(self, value):
        if value is not None:
            return phone_number_validator(value)
        return value

    def validate_other_phone(self, value):
        if value is not None:
            return phone_number_validator(value)
        return value

    def validate(self, attrs):
        """Validate university and email match"""
        validated_data = super().validate(attrs)

        user = self.context['request'].user

        email_activation_needed = False

        email = validated_data.get(
            'email',
            getattr(self.instance, 'email', None)
        )
        university = validated_data.get(
            'university',
            getattr(self.instance, 'university', None)
        )

        old_email = getattr(self.instance, 'email', None)

        new_email = attrs.get('email', None)
        new_university = attrs.get('university', None)

        if (new_email or new_university) and university:
            # Check that the email-university match is valid
            domains = university.domains.all()

            email_d = email.split("@", 1)[1]
            if not any(d.name.lower() == email_d.lower() for d in domains):
                raise serializers.ValidationError({
                    'email': [
                        _(
                            "You must use your university address to "
                            "choose this university."
                        )
                    ]
                })

        if new_email and new_email != old_email:
            # Email is already taken by another user
            if User.objects.filter(username=new_email).exists():
                raise serializers.ValidationError({
                    'email': [
                        _("An account with the same email already exist.")
                    ]
                })

            email_activation_needed = True
            # Create a ChangeEmail token containing the new email
            # Send an activation email containing the token key
            # When user clicks the link, only then the user email should be
            # changed.
            FRONTEND_SETTINGS = settings.LOCAL_SETTINGS[
                'FRONTEND_INTEGRATION'
            ]

            # Get the token of the saved user and send it with an email
            activate_token = ActionToken.objects.create(
                user=user,
                type='email_change',
                data={
                    "email": email,
                    "university_id": university.pk if university else None
                }
            ).key

            # Setup the url for the activation button in the email
            activation_url = FRONTEND_SETTINGS['EMAIL_CHANGE_CONFIRMATION']\
                .replace(
                "{{token}}",
                activate_token
            )

            # Send email to activate change of email
            services.notify_user_of_change_email(
                new_email,
                activation_url,
                user.first_name
            )

        if not email_activation_needed:
            validated_data['username'] = email
        else:
            validated_data.pop('email', None)
            validated_data.pop('university', None)

        return validated_data

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
        fields = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'university',
            'last_login',
            'date_joined',
            'academic_level',
            'academic_field',
            'gender',
            'language',
            'birthdate',
            'groups',
            'user_permissions',
            'tickets',
            'membership',
            'membership_end',
            'city',
            'personnal_restrictions',
            'academic_program_code',
            'faculty',
            'student_number',
            'volunteer_for_workplace',
            'hide_newsletter',
            'is_in_newsletter',
            'number_of_free_virtual_retreat',
            'membership_end_notification',
            'get_number_of_past_tomatoes',
            'get_number_of_future_tomatoes',
            'new_password',
            'username',
            'last_acceptation_terms_and_conditions',
            'password',
            'tomato_field_matrix',
            'current_month_tomatoes',
        ]
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
            'reservations',
            'membership_end',
            'tomato_field_matrix',
            'current_month_tomatoes',
        )


class ReservationUserSerializer(serializers.HyperlinkedModelSerializer):
    """
    Shorter user serializer for a reservation (block or retreat) detail
    """
    id = serializers.ReadOnlyField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.CharField()
    phone = serializers.CharField()
    personnal_restrictions = serializers.CharField()

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'url',
            'phone',
            'personnal_restrictions',
        ]
        read_only_fields = (
            'id',
            'url',
            'first_name',
            'last_name',
            'url',
            'phone',
            'personnal_restrictions',
        )


class UserSerializer(UserUpdateSerializer):
    """
    Complete serializer for user creation
    """
    email = serializers.EmailField(
        label=_('Email address'),
        max_length=254,
        required=True,
    )
    university = OrganizationSerializer(read_only=True)
    academic_level = AcademicLevelSerializer(read_only=True)
    academic_field = AcademicFieldSerializer(read_only=True)
    membership = MembershipSerializer(read_only=True)
    volunteer_for_workplace = serializers.HyperlinkedRelatedField(
        many=True,
        read_only=True,
        view_name='workplace-detail',
        source='workplaces',
    )
    is_in_newsletter = serializers.ReadOnlyField()
    get_number_of_past_tomatoes = serializers.ReadOnlyField()
    get_number_of_future_tomatoes = serializers.ReadOnlyField()

    def validate_email(self, value):
        """
        Lowercase all email addresses.
        """
        if User.objects.filter(email__iexact=value):
            raise serializers.ValidationError(_(
                "An account for the specified email "
                "address already exists."
            ))
        return value

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

        if content:
            raise serializers.ValidationError(content)

        return attrs

    def create(self, validated_data):
        """
        Check that the email domain correspond to the university.
        """
        user = User(**validated_data)

        # Hash the user's password
        user.set_password(validated_data['password'])

        # Put user inactive by default
        user.is_active = False

        # Auto accept terms and condition
        user.last_acceptation_terms_and_conditions = timezone.now()

        # Free ticket for new users
        user.tickets = 1

        user.save()

        return user

    class Meta:
        model = User
        fields = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'university',
            'last_login',
            'date_joined',
            'academic_level',
            'academic_field',
            'gender',
            'language',
            'birthdate',
            'groups',
            'user_permissions',
            'tickets',
            'membership',
            'membership_end',
            'city',
            'personnal_restrictions',
            'academic_program_code',
            'faculty',
            'student_number',
            'volunteer_for_workplace',
            'hide_newsletter',
            'is_in_newsletter',
            'number_of_free_virtual_retreat',
            'membership_end_notification',
            'get_number_of_past_tomatoes',
            'get_number_of_future_tomatoes',
            'password',
            'last_acceptation_terms_and_conditions',
            'tomato_field_matrix',
            'current_month_tomatoes',
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'new_password': {'write_only': True},
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
            'workplaces',
            'membership_end',
            'membership_end_notification',
            'last_acceptation_terms_and_conditions',
            'tomato_field_matrix',
            'current_month_tomatoes',
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

        # Return custom error if account is not activated
        try:
            user = User.objects.get(
                Q(email__iexact=username) | Q(username=username),
            )
            if user.is_active is False:
                msg = _('Your account is not activated. [code: not-activated]')
                raise serializers.ValidationError(msg, code='authorization')
        except User.DoesNotExist:
            pass

        # Manage email OR username login
        try:
            user_obj = User.objects.get(email__iexact=username)
            username = user_obj.username
        except User.DoesNotExist:
            pass

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password,
        )

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


class ResendEmailActivationSerializer(serializers.Serializer):

    email = serializers.CharField(required=True)


class ExportMediaSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = ExportMedia
        fields = '__all__'


class MailChimpSerializer(serializers.Serializer):

    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):

        try:
            response = mailchimp.add_to_list(
                email=validated_data['email'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name']
            )
        except MailChimpError as e:
            if e.args[0]['title'] == 'Member Exists':
                raise serializers.ValidationError({
                    'email': [
                        _(
                            "Email already register to this newsletter"
                        )
                    ]
                })
            raise serializers.ValidationError({
                'non_field_errors': [e.args[0]['detail']]
            })
        return validated_data
