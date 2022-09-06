from admin_auto_filters.filters import AutocompleteFilterFactory
from django.contrib import admin
from datetime import datetime
from dateutil.relativedelta import relativedelta

from log_management.tasks import export_anonymous_chrono_data
from log_management.models import (
    Log,
    EmailLog,
    ActionLog,
)


def export_anonymous_chrono_data_month(self, request, queryset):

    end_date = datetime.now()
    start_date = end_date - relativedelta(months=1)
    start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')
    export_anonymous_chrono_data.delay(request.user.id, start_date, end_date)


export_anonymous_chrono_data_month.short_description = \
    'export_anonymous_chrono_data_month'


class LogAdmin(admin.ModelAdmin):
    list_display = ('source', 'level', 'error_code', 'message', 'created')
    search_fields = (
        'message', 'additional_data', 'level', 'source', 'error_code',
        'traceback_data')
    list_filter = (
        'level',
        'source',
        'error_code',
    )
    date_hierarchy = 'created'


class EmailLogAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_email', 'type_email', 'nb_email_sent', 'created')
    search_fields = (
        'id', 'user_email', 'type_email',)
    list_filter = (
        'type_email',
        'user_email',
    )
    date_hierarchy = 'created'


class ActionLogAdmin(admin.ModelAdmin):
    actions = [
        export_anonymous_chrono_data_month,
    ]
    list_display = (
        'id',
        'user',
        'session_key',
        'source',
        'action',
        'created',
    )
    search_fields = (
        'id',
        'action',
        'source',
    )
    list_filter = (
        'source',
        'action',
        AutocompleteFilterFactory('User', 'user'),
    )
    date_hierarchy = 'created'

admin.site.register(Log, LogAdmin)
admin.site.register(EmailLog, EmailLogAdmin)
admin.site.register(ActionLog, ActionLogAdmin)
