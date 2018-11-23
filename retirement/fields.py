import pytz

from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _


class TimezoneField(serializers.CharField):
    def to_internal_value(self, value):
        tz = super().to_representation(value)
        try:
            return str(pytz.timezone(tz))
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError(_("Unknown timezone"))
