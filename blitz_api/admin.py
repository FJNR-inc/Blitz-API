from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import AbstractUser, Permission
from django.utils.translation import ugettext_lazy as _
from import_export.admin import ExportActionModelAdmin
from modeltranslation.admin import TranslationAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import (AcademicField, AcademicLevel, ActionToken, Domain,
                     Organization, TemporaryToken, User)
from .resources import (AcademicFieldResource, AcademicLevelResource,
                        OrganizationResource, UserResource)


class CustomUserChangeForm(UserChangeForm):
    """ Required to update users in Django Admin with proper user model """
    class Meta(UserChangeForm.Meta):
        model = User


class CustomUserCreationForm(UserCreationForm):
    """ Required to create users in Django Admin with proper user model """
    class Meta(UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data['username']
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username
        raise forms.ValidationError(self.error_messages['duplicate_username'])


class CustomUserAdmin(UserAdmin, SimpleHistoryAdmin, ExportActionModelAdmin):
    """ Required to display extra fields of users in Django Admin """
    resource_class = UserResource
    form = CustomUserChangeForm
    search_fields = ['first_name', 'last_name', 'email', 'id']

    def __init__(self, *args, **kwargs):
        super(CustomUserAdmin, self).__init__(*args, **kwargs)

        abstract_fields = [field.name for field in AbstractUser._meta.fields]
        user_fields = [field.name for field in self.model._meta.fields]

        self.fieldsets += (
            (_('Extra fields'), {
                'fields': [
                    f for f in user_fields if (
                        f not in abstract_fields and
                        f != self.model._meta.pk.name
                    )
                ],
            }),
        )


class DomainInline(admin.StackedInline):
    model = Domain
    can_delete = True
    show_change_link = True
    verbose_name_plural = _('Domains')
    fk_name = 'organization'
    extra = 0  # No one extra blank field in the admin representation


class CustomOrganizationAdmin(SimpleHistoryAdmin, TranslationAdmin,
                              ExportActionModelAdmin):
    resource_class = OrganizationResource
    inlines = (DomainInline, )


class ActionTokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'type', 'user',)
    search_fields = ('type', 'user__email',)
    list_filter = (
        'type',
        'expires',
    )


class TemporaryTokenAdmin(SimpleHistoryAdmin):
    list_display = ('key', 'user',)
    search_fields = ('user__email',)
    list_filter = (
        'expires',
    )


class AcademicFieldAdmin(SimpleHistoryAdmin, TranslationAdmin,
                         ExportActionModelAdmin):
    resource_class = AcademicFieldResource


class AcademicLevelAdmin(SimpleHistoryAdmin, TranslationAdmin,
                         ExportActionModelAdmin):
    resource_class = AcademicLevelResource


admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization, CustomOrganizationAdmin)
admin.site.register(Domain, SimpleHistoryAdmin)
admin.site.register(ActionToken, ActionTokenAdmin)
admin.site.register(TemporaryToken, TemporaryTokenAdmin)
admin.site.register(AcademicField, AcademicFieldAdmin)
admin.site.register(AcademicLevel, AcademicLevelAdmin)
