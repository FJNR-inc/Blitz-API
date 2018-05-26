from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from django.utils.translation import ugettext_lazy as _

from location.models import Address
from location.serializers import AddressBasicSerializer

from .models import Workplace, Picture, Period


class WorkplaceSerializer(serializers.HyperlinkedModelSerializer):
    location = AddressBasicSerializer(
        # This overrides UniqueTogether constraint of the Address serializer
        validators=[],
        help_text=_("Address of the workplace."),
    )

    def validate_location(self, value):
        """
        Checks that the address exists. Since the AddressBasicSerializer
        returns a dictionary containing the address' informations, we
        unpack that dictionary as kwargs for the Address model query.
        """
        address = Address.objects.filter(**value)

        if address:
            return address[0]
        raise serializers.ValidationError(
            _("This address does not exist.")
        )

    class Meta:
        model = Workplace
        fields = '__all__'
        extra_kwargs = {
            'details': {'help_text': _("Description of the workplace.")},
            'name': {
                'help_text': _("Name of the workplace."),
                'validators': [
                    UniqueValidator(queryset=Workplace.objects.all())
                ],
            },
            'seats': {'help_text': _("Number of available seats.")},
        }


class PictureSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Picture
        fields = '__all__'
        extra_kwargs = {
            'workplace': {
                'help_text': _("Workplace represented by the picture.")
            },
            'name': {
                'help_text': _("Name of the picture."),
            },
            'picture': {
                'help_text': _("File to upload."),
            }
        }


class PeriodSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Period
        fields = '__all__'
        extra_kwargs = {
            'workplace': {
                'required': True,
                'help_text': _("Workplaces to which this period applies.")
            },
            'name': {
                'required': True,
                'help_text': _("Name of the picture."),
            },
            'price': {
                'required': True,
                'help_text': _("Hourly rate applied to this period.")
            },
            'is_active': {
                'required': True,
                'help_text': _("Whether users can see this period or not.")
            },
            'start_date': {
                'required': True,
            },
            'end_date': {
                'required': True,
            },
        }
