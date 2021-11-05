from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers


from tomato.models import (
    Message,
    Attendance,
)

User = get_user_model()


class MessageSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    user = serializers.HyperlinkedRelatedField(
        'user-detail',
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = Message
        fields = '__all__'

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

    class Meta:
        model = Attendance
        fields = '__all__'


class AttendanceDeleteKeySerializer(serializers.Serializer):
    key = serializers.CharField()