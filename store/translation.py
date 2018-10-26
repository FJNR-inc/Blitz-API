import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Membership)
class MembershipTranslationOptions(TranslationOptions):
    fields = (
        'name',
        'details',
    )


@register(models.Package)
class PackageTranslationOptions(TranslationOptions):
    fields = (
        'name',
        'details',
    )


simple_history.register(models.Membership, inherit=True)
simple_history.register(models.Package, inherit=True)
