"""Store URL Configuration"""
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "tomato"

router_extra = OptionalSlashSimpleRouter()

# Create a router and register our viewsets with it.
router = OptionalSlashSimpleRouter()
router.register('messages', views.MessageViewSet)
router.register('reports', views.ReportViewSet)
router.register('attendances', views.AttendanceViewSet)
router.register('tomatoes', views.TomatoViewSet)

router.registry.extend(router_extra.registry)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
