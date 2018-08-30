from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class S3MediaStorage(S3Boto3Storage):
    """
    This class is needed to specify the folder in which media assets will be
    stored in the S3 bucket.
    """
    location = settings.AWS_S3_MEDIA_DIR
    bucket_name = settings.AWS_STORAGE_MEDIA_BUCKET_NAME
    custom_domain = settings.AWS_S3_MEDIA_CUSTOM_DOMAIN
    file_overwrite = False


class S3StaticStorage(S3Boto3Storage):
    """
    This class is needed to specify the folder in which static assets will be
    stored in the S3 bucket.
    """
    location = settings.AWS_S3_STATIC_DIR
    bucket_name = settings.AWS_STORAGE_STATIC_BUCKET_NAME
    custom_domain = settings.AWS_S3_STATIC_CUSTOM_DOMAIN
