from django.contrib import admin
from tomato.models import (
    Message,
    Attendance,
)

admin.site.register(Message)
admin.site.register(Attendance)