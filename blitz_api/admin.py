from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import AbstractUser, Permission
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from simple_history.admin import SimpleHistoryAdmin

from .models import (
    User, Organization, Domain, TemporaryToken, ActionToken, AcademicField,
    AcademicLevel,
)


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


class CustomUserAdmin(UserAdmin, SimpleHistoryAdmin):
    """ Required to display extra fields of users in Django Admin """
    form = CustomUserChangeForm

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
    verbose_name_plural = _('Domains')
    fk_name = 'organization'
    extra = 0  # No one extra blank field in the admin representation


class CustomOrganizationAdmin(SimpleHistoryAdmin):
    inlines = (DomainInline, )


class ActionTokenAdmin(admin.ModelAdmin):
    list_display = ('key', 'type', 'user',)
    search_fields = ('type', 'user',)


admin.site.register(User, CustomUserAdmin)
admin.site.register(Organization, CustomOrganizationAdmin)
admin.site.register(Domain, SimpleHistoryAdmin)
admin.site.register(ActionToken, ActionTokenAdmin)
admin.site.register(TemporaryToken, SimpleHistoryAdmin)
admin.site.register(AcademicField, SimpleHistoryAdmin)
admin.site.register(AcademicLevel, SimpleHistoryAdmin)
