from django.contrib import admin

from . import models
from django.utils.translation import ugettext_lazy as _


class ExecutionInline(admin.StackedInline):
    model = models.Execution
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Executions')
    fk_name = 'task'


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
        'task',
        'http_code'
    )
    autocomplete_fields = ('task',)


admin.site.register(models.Task, TaskAdmin)
admin.site.register(models.Execution, ExecutionAdmin)
