"""mobile_api_extensions URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.urls import include, path, re_path
from rest_framework.routers import SimpleRouter

from .api import (
    BlocksInCourseViewExtended,
    CommentViewSetExtended,
    UserCourseEnrollmentsListExtended
)

ROUTER = SimpleRouter()
ROUTER.register("comments", CommentViewSetExtended, basename="comment-extended")

urlpatterns = [
    re_path(
        r'^(?P<api_version>v(1|0.5))/users/' + settings.USERNAME_PATTERN + '/course_enrollments/$',
        UserCourseEnrollmentsListExtended.as_view(),
        name='courseenrollment-detail'
    ),
    re_path(r'^discussion/v1/', include(ROUTER.urls)),
    path(
        'v1/blocks/',
        BlocksInCourseViewExtended.as_view(),
        kwargs={'hide_access_denials': True},
        name="blocks_in_course"
    ),
    path(
        'v2/blocks/',
        BlocksInCourseViewExtended.as_view(),
        name="blocks_in_course"
    ),
]
