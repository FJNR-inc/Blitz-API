
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    def __init__(self):
        super().__init__()
        self.trailing_slash = '/?'


app_name = "ckeditor_api"

router = OptionalSlashSimpleRouter()
router.register('ckeditor_page', views.CKEditorPageViewSet)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
