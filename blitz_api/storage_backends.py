"""
GoogleCloudStorage extensions suitable for handing Django's
Static and Media files.
Requires following settings:
MEDIA_URL, GS_MEDIA_BUCKET_NAME
STATIC_URL, GS_STATIC_BUCKET_NAME
In addition to
https://django-storages.readthedocs.io/en/latest/backends/gcloud.html
"""

from django.conf import settings
from storages.backends.gcloud import GoogleCloudStorage
from storages.utils import setting


class GoogleCloudMediaStorage(GoogleCloudStorage):
    """GoogleCloudStorage suitable for Django's Media files."""

    def __init__(self, **kwargs):
        if not settings.MEDIA_URL:
            raise Exception('MEDIA_URL has not been configured')
        kwargs['bucket_name'] = setting('GS_MEDIA_BUCKET_NAME')
        super(GoogleCloudMediaStorage, self).__init__(**kwargs)