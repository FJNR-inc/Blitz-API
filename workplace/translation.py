import simple_history
from modeltranslation.translator import TranslationOptions, register

from . import models


@register(models.Workplace)
class WorkplaceTranslationOptions(TranslationOptions):
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


@register(models.Period)
class PeriodTranslationOptions(TranslationOptions):
    fields = ('name', )


simple_history.register(models.Workplace, inherit=True)
simple_history.register(models.Picture, inherit=True)
simple_history.register(models.Period, inherit=True)
