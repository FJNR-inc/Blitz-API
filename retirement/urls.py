"""Retirements URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from rest_framework.routers import SimpleRouter
from django.urls import path
from django.conf.urls import include

from . import views


class OptionalSlashSimpleRouter(SimpleRouter):
    """ Subclass of SimpleRouter to make the trailing slash optional """

    def __init__(self, *args, **kwargs):
        super(SimpleRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


app_name = "retirement"

# Create a router and register our viewsets with it.
router = OptionalSlashSimpleRouter()
router.register('retirements', views.RetirementViewSet)
router.register('pictures', views.PictureViewSet)
router.register('reservations', views.ReservationViewSet)
router.register('wait_queues', views.WaitQueueViewSet)
router.register('wait_queue_notifications', views.WaitQueueNotificationViewSet)

urlpatterns = [
    path('', include(router.urls)),  # includes router generated URL
]
