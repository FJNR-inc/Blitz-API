
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """

    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "cron_manager"

router = OptionalSlashSimpleRouter()
router.register('tasks', views.TaskViewSet)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
