from rest_framework import serializers

from .models import (
    Task
)


class TaskSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Task
        fields = '__all__'
