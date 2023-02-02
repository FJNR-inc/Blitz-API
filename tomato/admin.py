from admin_auto_filters.filters import AutocompleteFilter, \
    AutocompleteFilterFactory
from django.contrib import admin
from tomato.models import (
    Message,
    Attendance,
    Report, Tomato,
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


class TomatoAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'number_of_tomato',
        'acquisition_date',
        'created_at',
        'updated_at',
    )
    list_filter = (
        AutocompleteFilterFactory('User', 'user'),
    )

    autocomplete_fields = ['user']


admin.site.register(Message)
admin.site.register(Attendance)
admin.site.register(Report, ReportAdmin)
admin.site.register(Tomato, TomatoAdmin)
