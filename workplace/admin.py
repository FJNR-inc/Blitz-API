from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from .models import Workplace, Picture


class PictureAdminInline(admin.TabularInline):
    model = Picture
    readonly_fields = ('picture_tag',)


class WorkplaceAdmin(admin.ModelAdmin):
    inlines = (PictureAdminInline,)


class PictureAdmin(admin.ModelAdmin):
    list_display = ('name', 'workplace', 'picture_tag',)


admin.site.register(Workplace, WorkplaceAdmin)
admin.site.register(Picture, PictureAdmin)
