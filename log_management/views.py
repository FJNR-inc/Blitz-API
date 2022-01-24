from log_management.models import ActionLog

from rest_framework import (
    viewsets,
)

from log_management.serializers import ActionLogSerializer

from rest_framework.permissions import (
    IsAdminUser,
)


class ActionLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActionLogSerializer
    queryset = ActionLog.objects.all()

    def get_permissions(self):
        if self.action in ['create']:
            permission_classes = []
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]
