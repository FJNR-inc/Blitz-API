import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.AcademicLevel)
class AcademicLevelTranslationOptions(TranslationOptions):
    fields = ('name', )


@register(models.AcademicField)
class AcademicFieldTranslationOptions(TranslationOptions):
    fields = ('name', )


@register(models.Organization)
class OrganizationTranslationOptions(TranslationOptions):
    fields = ('name', )


simple_history.register(models.AcademicLevel, inherit=True)
simple_history.register(models.AcademicField, inherit=True)
simple_history.register(models.Organization, inherit=True)
