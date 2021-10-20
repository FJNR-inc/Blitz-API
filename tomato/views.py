from django.shortcuts import render
from tomato.models import (
    Message,
    Attendance,
)
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import (
    status,
    viewsets,
)
from rest_framework.decorators import action
from tomato.serializers import (
    MessageSerializer,
    AttendanceSerializer,
)
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    queryset = Message.objects.all()
    ordering = ('posted_at',)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        elif self.action in ['create']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    queryset = Attendance.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'current_number']:
            permission_classes = []
        else:
            permission_classes = [IsAdminUser]

        return [permission() for permission in permission_classes]

    @action(detail=False, permission_classes=[])
    def current_number(self, request):
        beginning_of_period = timezone.now().replace(minute=0, second=0, microsecond=0)

        list_of_attendance = Attendance.objects.filter(
            created_at__gte=beginning_of_period
        )

        number_of_attendance = 0
        list_of_user = []

        for attendance in list_of_attendance:
            if attendance.user:
                if attendance.user not in list_of_user:
                    number_of_attendance += 1
                    list_of_user.append(attendance.user)
            else:
                number_of_attendance += 1

        return Response(
            status=status.HTTP_200_OK,
            data={
                'number_of_attendance': number_of_attendance,
            },
        )
