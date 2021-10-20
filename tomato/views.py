from django.shortcuts import render
from tomato.models import Message
from rest_framework import viewsets
from tomato.serializers import MessageSerializer
from rest_framework.permissions import IsAuthenticated


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    queryset = Message.objects.all()
    ordering = ('posted_at',)

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = []
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]