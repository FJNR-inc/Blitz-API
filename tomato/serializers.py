import random
import decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from tomato.models import (
    Message,
    Attendance,
    Report, Tomato,
)

User = get_user_model()


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    reported = serializers.SerializerMethodField()
    user = serializers.HyperlinkedRelatedField(
        'user-detail',
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Message
        fields = '__all__'

    def get_reported(self, obj):
        return obj.reports.all().count() > 0

    def create(self, validated_data):
        # Check that only admin can specify a owner
        if validated_data.get('user', None):
            if not self.context['request'].user.is_staff:
                raise serializers.ValidationError({
                    'owner': [
                        'Only staffs can specify an '
                        'other user than themselves'
                    ]
                })
        else:
            validated_data['user'] = self.context['request'].user

        return super(MessageSerializer, self).create(validated_data)


class AttendanceSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    longitude = serializers.DecimalField(
        max_digits=18,
        decimal_places=15,
        required=False,
    )

    latitude = serializers.DecimalField(
        max_digits=18,
        decimal_places=15,
        required=False,
    )

    class Meta:
        model = Attendance
        fields = '__all__'

    def validate_longitude(self, value):
        return self.protect_gps_position(value)

    def validate_latitude(self, value):
        return self.protect_gps_position(value)

    def protect_gps_position(self, value):
        # The number of GPS decimal point allow us to enhance the approx.
        # of the exact position:
        #
        # - 2 decimals points: ~1/4 miles
        # - 3 decimals points: ~40 feet
        # - 4 decimals points: ~12 feet
        #
        # The idea here is to have a 2 decimal points precision
        # but without having multiple people at the exact same place,
        # in this context we will just cut at 3 decimal and randomly
        # change the last one to be in the disk of 1/4 miles radius
        # around the real point.

        third_digit = decimal.Decimal(0.001).quantize(decimal.Decimal('0.001'))
        third_digit = third_digit * random.randrange(1, 10)

        if value:
            value = value.quantize(
                decimal.Decimal('0.01')
            ) + third_digit

        return value


class ReportSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    user = serializers.HyperlinkedRelatedField(
        'user-detail',
        queryset=User.objects.all(),
        required=False,
    )
    message = serializers.HyperlinkedRelatedField(
        'message-detail',
        queryset=Message.objects.all(),
    )

    class Meta:
        model = Report
        fields = '__all__'

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        report = Report.objects.create(**validated_data)
        report.send_report_notification()

        return report


class TomatoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    user = serializers.HyperlinkedRelatedField(
        'user-detail',
        read_only=True,
    )

    class Meta:
        model = Tomato
        fields = ['id', 'url', 'user', 'number_of_tomato', 'source',
                  'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        return super(TomatoSerializer, self).create(validated_data)


class AttendanceDeleteKeySerializer(serializers.Serializer):
    key = serializers.CharField()
