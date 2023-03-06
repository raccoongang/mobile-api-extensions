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
from common.djangoapps.util.views import ensure_valid_course_key

from .api import (
    BlocksInCourseViewExtended,
    CommentViewSetExtended,
    UserCourseEnrollmentsListExtended,
    CourseDetailViewExtended,
    CourseProgressView,
    DeactivateLogoutViewExtended,
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
    re_path(r'^v1/courses/{}/progress/$'.format(settings.COURSE_ID_PATTERN),
        ensure_valid_course_key(CourseProgressView.as_view()),
        name='api-course-progress'
    ),
    re_path(fr'^v1/courses/{settings.COURSE_KEY_PATTERN}',
        CourseDetailViewExtended.as_view(),
        name="course-detail"
    ),
    path(
        'user/v1/accounts/deactivate_logout/', DeactivateLogoutViewExtended.as_view(),
        name='deactivate_logout'
    ),
]
