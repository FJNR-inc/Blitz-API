"""Blitz-API URL Configuration

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
from rest_framework.documentation import include_docs_urls
from rest_framework.routers import DefaultRouter
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls import include

from . import views


class OptionalSlashDefaultRouter(DefaultRouter):
    """ Subclass of DefaultRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(DefaultRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


# Create a router and register our viewsets with it.
router = OptionalSlashDefaultRouter()
router.register('users', views.UserViewSet)
router.register('domains', views.DomainViewSet)
router.register('organizations', views.OrganizationViewSet)

urlpatterns = [
    path(
        'authentication',
        views.ObtainTemporaryAuthToken.as_view(),
        name='token_api'
    ),
    path(
        'users/activate',
        views.UsersActivation.as_view(),
        name='users_activation',
    ),
    # Forgot password
    path(
        'reset_password',
        views.ResetPassword.as_view(),
        name='reset_password'
        ),
    path(
        'change_password',
        views.ChangePassword.as_view(),
        name='change_password'
    ),
    path(
        'admin/', admin.site.urls
    ),
    path(
        'docs/',
        include_docs_urls(
            title=settings.LOCAL_SETTINGS['ORGANIZATION'] + " API",
            authentication_classes=[],
            permission_classes=[]
        )
    ),
    path('api-auth/', include('rest_framework.urls')),
    path('', include(router.urls)),  # includes router generated URL
]
