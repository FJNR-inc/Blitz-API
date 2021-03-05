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
from django.conf.urls import include, url
from django.conf.urls.static import static

from cron_manager.views import CronViewFunction
from workplace.urls import router as workplace_router
from store.urls import router as store_router
from retirement.urls import router as retirement_router
from cron_manager.urls import router as cron_manager_router
from ckeditor_api.urls import router as ckeditor_api_router

from . import views


class OptionalSlashDefaultRouter(DefaultRouter):
    """ Subclass of DefaultRouter to make the trailing slash optional """
    def __init__(self, *args, **kwargs):
        super(DefaultRouter, self).__init__(*args, **kwargs)
        self.trailing_slash = '/?'


# Create a router and register our viewsets with it.
router = OptionalSlashDefaultRouter()

# External workplace application
# Their urls are directly appended to the main router
# The retreat app is not included here because we needed a url prefix, thus
#   it is included separately at the bottom of this file.
router.registry.extend(workplace_router.registry)
router.registry.extend(store_router.registry)
router.registry.extend(cron_manager_router.registry)
router.registry.extend(ckeditor_api_router.registry)
# router.registry.extend(retirement_router.registry)

router.register('users', views.UserViewSet)
router.register('domains', views.DomainViewSet)
router.register('organizations', views.OrganizationViewSet)
router.register('academic_levels', views.AcademicLevelViewSet)
router.register('academic_fields', views.AcademicFieldViewSet)
router.register(
    'authentication',
    views.TemporaryTokenDestroy,
    basename="authentication",
)

router.register('export_media', views.ExportMediaViewSet)

urlpatterns = [
    path(
        'authentication',
        views.ObtainTemporaryAuthToken.as_view(),
        name='token_api'
    ),
    path(
        'mail_chimp',
        views.MailChimpView.as_view(),
        name='mail_chimp'
    ),
    path(
        'users/activate',
        views.UsersActivation.as_view(),
        name='users_activation',
    ),
    path(
        'profile',
        views.UserViewSet.as_view({
            'get': 'retrieve'
        }),
        name='profile',
        kwargs={'pk': 'me'},
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
    # The retreat app must be namespaced due to conflicting resources names
    #   (reservations & pictures)
    path(
        'retreat/',
        include((retirement_router.urls, 'retreat'), namespace='retreat')
    ),
    url(
        'cron-function/',
        CronViewFunction
    ),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
