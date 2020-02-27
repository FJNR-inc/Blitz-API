from django.db import models
from django.utils.translation import ugettext_lazy as _


class CKEditorPage(models.Model):

    key = models.CharField(
        verbose_name=_('Key'),
        unique=True,
        max_length=255
    )

    data = models.TextField(
        verbose_name=_('Data'),
        blank=True
    )

    updated_at = models.DateTimeField(
        verbose_name=_('Data'),
        auto_now_add=True
    )

    def __str__(self):
        return self.key
