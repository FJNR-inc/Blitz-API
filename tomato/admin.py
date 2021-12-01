from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin
from tomato.models import (
    Message,
    Attendance,
    Report,
)


class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'


class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'created_at',
        'reason',
        'author',
    )
    list_filter = (
        UserFilter,
        'created_at',
    )

    autocomplete_fields = ['user']

    @staticmethod
    def author(report):
        return report.message.user

    class Media:
        pass


admin.site.register(Message)
admin.site.register(Attendance)
admin.site.register(Report, ReportAdmin)
