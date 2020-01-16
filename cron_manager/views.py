
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .models import (
     Task
)

from . import serializers


class TaskViewSet(viewsets.ModelViewSet):

    serializer_class = serializers.TaskSerializer
    queryset = Task.objects.all()
    permission_classes = [IsAdminUser]
