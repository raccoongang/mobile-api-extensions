from django.urls import path, re_path, include
from django.views.decorators.csrf import csrf_exempt

from .views import (
    AuthorizationCodeExchangeView,
    auth_mobile,
    complete_mobile,
    redirect_to_mobile_deeplink,
    redirect_to_mobile,
)
from .utils import is_enabled_mobile


def append_mobile_urls(urlpatterns):
    """
    Appends mobile-specific authentication URLs if mobile auth is enabled.
    """
    if is_enabled_mobile():
        urlpatterns.append(
            re_path(
                r'^exchange_authorization_code/?$',
                csrf_exempt(AuthorizationCodeExchangeView.as_view()),
                name='exchange_authorization_code',
            )
        )
    return urlpatterns


urlpatterns = [
    re_path(r'^auth/login/(?P<backend>[^/]+)/$', auth_mobile, name='social_login_override'),
    re_path(r'^auth/complete/(?P<backend>[^/]+)/$', complete_mobile, name='social_complete_override'),
    path('auth/', include('social_django.urls', namespace='social')),
    path('sso_deeplink', redirect_to_mobile_deeplink, name='sso-deeplink'),
    re_path(r'^auth/login/mobile/(?P<backend_name>[^/]+)/$', redirect_to_mobile, name='redirect-mobile'),
]