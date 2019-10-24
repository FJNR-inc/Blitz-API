from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from .models import AcademicField, AcademicLevel, Domain, Organization, User
from store.models import Membership


# django-import-export models declaration
# These represent the models data that will be importd/exported
class AcademicFieldResource(resources.ModelResource):

    class Meta:
        model = AcademicField
        fields = ('id', 'name',)
        export_order = ('id', 'name',)


class AcademicLevelResource(resources.ModelResource):

    class Meta:
        model = AcademicLevel
        fields = ('id', 'name',)
        export_order = ('id', 'name',)


class OrganizationResource(resources.ModelResource):

    domains = fields.Field(
        column_name='domains',
        attribute='domains',
        widget=ManyToManyWidget(Domain, ',', 'name'),
    )

    class Meta:
        model = Organization
        fields = ('id', 'name', 'domains')
        export_order = ('id', 'name', 'domains')


class UserResource(resources.ModelResource):

    academic_field = fields.Field(
        column_name='academic_field',
        attribute='academic_field',
        widget=ForeignKeyWidget(AcademicField, 'name'),
    )

    academic_level = fields.Field(
        column_name='academic_level',
        attribute='academic_level',
        widget=ForeignKeyWidget(AcademicLevel, 'name'),
    )

    university = fields.Field(
        column_name='university',
        attribute='university',
        widget=ForeignKeyWidget(Organization, 'name'),
    )

    membership = fields.Field(
        column_name='membership',
        attribute='membership',
        widget=ForeignKeyWidget(Membership, 'name'),
    )

    class Meta:
        model = User
        exclude = (
            'password',
            'username',
            'groups',
            'user_permissions'
        )
        export_order = (
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'other_phone',
            'birthdate',
            'gender',
            'university',
            'academic_field',
            'academic_level',
            'membership',
            'membership_end',
            'tickets',
            'date_joined',
            'last_login',
            'language',
        )
