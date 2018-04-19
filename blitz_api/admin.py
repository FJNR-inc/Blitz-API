from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Organization, Domain

from django.utils.translation import ugettext_lazy as _


class DomainInline(admin.StackedInline):
    model = Domain
    can_delete = True
    verbose_name_plural = _('Domains')
    fk_name = 'organization'
    extra = 0  # No one extra blank field in the admin representation


class CustomOrganizationAdmin(admin.ModelAdmin):
    inlines = (DomainInline, )


admin.site.register(User, UserAdmin)
admin.site.register(Organization, CustomOrganizationAdmin)
admin.site.register(Domain)
