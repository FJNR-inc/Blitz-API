import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Retirement)
class RetirementTranslationOptions(TranslationOptions):
    fields = (
        'name',
        'details',
        'country',
        'state_province',
        'city',
        'address_line1',
        'address_line2',
    )


@register(models.Picture)
class PictureTranslationOptions(TranslationOptions):
    fields = ('name', )


simple_history.register(models.Retirement, inherit=True)
simple_history.register(models.Picture, inherit=True)
