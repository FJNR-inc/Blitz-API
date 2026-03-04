
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    trailing_slash = '/?'


app_name = "cron_manager"

router = OptionalSlashSimpleRouter()
router.register('tasks', views.TaskViewSet)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
