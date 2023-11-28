from admin_auto_filters.filters import AutocompleteFilter
from django.contrib import admin

from . import models
from django.utils.translation import gettext_lazy as _
from django_admin_inline_paginator.admin import TabularInlinePaginated


class TaskFilter(AutocompleteFilter):
    title = 'Task'
    field_name = 'task'


class ExecutionInline(TabularInlinePaginated):
    model = models.Execution
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Executions')
    fk_name = 'task'
    readonly_fields = ('created_at',)
    max_num = 10
    per_page = 5


class TaskAdmin(admin.ModelAdmin):
    inlines = (ExecutionInline,)
    list_display = (
        'id',
        'description',
        'execution_datetime',
        'execution_interval',
        'active',
        'created_at'
    )
    list_filter = (
        'description',
        'active'
    )
    search_fields = (
        'description',
        'id',
    )


class ExecutionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'task',
        'created_at',
        'executed_at',
        'success',
        'http_code'
    )
    list_filter = (
        'success',
        TaskFilter,
        'http_code'
    )
    autocomplete_fields = ('task',)
    readonly_fields = ('created_at',)

    # https://github.com/farhan0581/django-admin-autocomplete-filter/blob/master/README.md#usage
    class Media:
        pass


admin.site.register(models.Task, TaskAdmin)
admin.site.register(models.Execution, ExecutionAdmin)
