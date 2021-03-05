from django.http import HttpResponse
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .cron_function import execute_tasks
from .models import (
     Task
)

from . import serializers


class TaskViewSet(viewsets.ModelViewSet):

    serializer_class = serializers.TaskSerializer
    queryset = Task.objects.all()
    permission_classes = [IsAdminUser]


# https://medium.com/@michael.lisboa/2-minutes-to-set-up-a-cron-job-on-google-cloud-app-engine-f5e2aa847f00
def CronViewFunction(request):
    if request.META.get('HTTP_X_APPENGINE_CRON'):
        # Request comes from GCP Cron, so do a bunch of stuff.
        execute_tasks()
    else:
        # Not allowed
        return HttpResponse(status="403")

    return HttpResponse(status="200")
