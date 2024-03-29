"""Store URL Configuration"""
from rest_framework.routers import SimpleRouter, Route
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "log_management"

router_extra = OptionalSlashSimpleRouter()

# Create a router and register our viewsets with it.
router = OptionalSlashSimpleRouter()
router.register('actionlogs', views.ActionLogViewSet)

router.registry.extend(router_extra.registry)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
