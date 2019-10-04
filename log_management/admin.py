
from django.contrib import admin

from log_management.models import Log


class LogAdmin(admin.ModelAdmin):
    list_display = ('source', 'level', 'error_code', 'message',)
    search_fields = (
        'message', 'additional_data', 'level', 'source', 'error_code',
        'traceback_data')
    list_filter = (
        'level',
        'source',
        'error_code',
    )


admin.site.register(Log, LogAdmin)
