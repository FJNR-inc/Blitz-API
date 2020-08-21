import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.RetreatType)
class RetreatTypeTranslationOptions(TranslationOptions):
    fields = (
        'name',
    )


@register(models.Retreat)
class RetreatTranslationOptions(TranslationOptions):
    fields = (
        'country',
        'state_province',
        'city',
        'address_line1',
        'address_line2',
    )


@register(models.Picture)
class PictureTranslationOptions(TranslationOptions):
    fields = ('name', )


simple_history.register(models.RetreatType, inherit=True)
simple_history.register(models.Retreat, inherit=True)
simple_history.register(models.Picture, inherit=True)
