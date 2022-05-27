from django.contrib.auth import get_user_model

from rest_framework import serializers

from log_management.models import ActionLog

User = get_user_model()


class ActionLogSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    user = serializers.HyperlinkedRelatedField(
        'user-detail',
        queryset=User.objects.all(),
        required=False,
    )

    class Meta:
        model = ActionLog
        fields = '__all__'

    def create(self, validated_data):
        # Check that only admin can specify a owner
        user = validated_data.get('user', None)
        current_user = self.context['request'].user

        if user:
            if user != current_user and not current_user.is_staff:
                raise serializers.ValidationError({
                    'owner': [
                        'Only staffs can specify a user'
                    ]
                })
        elif self.context['request'].user.is_authenticated:
            validated_data['user'] = self.context['request'].user

        return super(ActionLogSerializer, self).create(validated_data)
