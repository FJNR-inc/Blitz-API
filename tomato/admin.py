from django.contrib import admin
from tomato.models import (
    Message,
    Attendance,
    Report,
)

admin.site.register(Message)
admin.site.register(Attendance)
admin.site.register(Report)
