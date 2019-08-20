import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.BaseProduct)
class BaseProductTranslationOptions(TranslationOptions):
    fields = (
        'name',
        'details',
    )


@register(models.Membership)
class MembershipTranslationOptions(TranslationOptions):
    fields = (
    )


@register(models.Package)
class PackageTranslationOptions(TranslationOptions):
    fields = (
    )


@register(models.OptionProduct)
class OptionProductTranslationOptions(TranslationOptions):
    fields = (
    )


simple_history.register(models.Membership, inherit=True)
simple_history.register(models.Package, inherit=True)
simple_history.register(models.BaseProduct, inherit=True)
simple_history.register(models.OptionProduct, inherit=True)
