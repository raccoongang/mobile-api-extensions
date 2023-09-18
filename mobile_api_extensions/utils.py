import search
from django.conf import settings
from edx_django_utils.monitoring import function_trace
from lms.djangoapps import branding
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.course_api.api import get_effective_user
from lms.djangoapps.courseware.courses import get_courses
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.lib.api.view_utils import LazySequence


@function_trace('get_courses')
def get_courses(user, org=None, filter_=None, permissions=None):
    """
    Return a LazySequence of courses available, optionally filtered by org code
    (case-insensitive) or a set of permissions to be satisfied for the specified
    user.
    """

    courses = branding.get_visible_courses(
        org=org,
        filter_=filter_,
    ).prefetch_related(
        'modes',
    ).select_related(
        'image_set'
    )

    permissions = set(permissions or '')
    permission_name = configuration_helpers.get_value(
        'COURSE_CATALOG_VISIBILITY_PERMISSION',
        settings.COURSE_CATALOG_VISIBILITY_PERMISSION
    )
    permissions.add(permission_name)

    courses = {c for c in courses if all(has_access(user, p, c) for p in permissions)}
    return LazySequence(
        iter(courses),
        est_len=len(courses)
    )


def _filter_by_search(course_queryset, search_term):
    """
    Filters a course queryset by the specified search term.
    """
    if not settings.FEATURES['ENABLE_COURSEWARE_SEARCH'] or not search_term:
        return course_queryset

    # Return all the results, 10K is the maximum allowed value for ElasticSearch.
    # We should use 0 after upgrading to 1.1+:
    #   - https://github.com/elastic/elasticsearch/commit/8b0a863d427b4ebcbcfb1dcd69c996c52e7ae05e
    results_size_infinity = 10000

    search_courses = search.api.course_discovery_search(
        search_term,
        size=results_size_infinity,
    )

    search_courses_ids = {course['data']['id'] for course in search_courses['results']}
    courses = [course for course in course_queryset if str(course.id) in search_courses_ids]
    return LazySequence(
        iter(courses),
        est_len=len(courses)
    )


def list_courses(request,
                 username,
                 org=None,
                 filter_=None,
                 search_term=None,
                 permissions=None):
    """
    Yield all available courses.

    The courses returned are all be visible to the user identified by
    `username` and the logged in user should have permission to view courses
    available to that user.

    Arguments:
        request (HTTPRequest):
            Used to identify the logged-in user and to instantiate the course
            module to retrieve the course about description
        username (string):
            The name of the user the logged-in user would like to be
            identified as

    Keyword Arguments:
        org (string):
            If specified, visible `CourseOverview` objects are filtered
            such that only those belonging to the organization with the provided
            org code (e.g., "HarvardX") are returned. Case-insensitive.
        filter_ (dict):
            If specified, visible `CourseOverview` objects are filtered
            by the given key-value pairs.
        search_term (string):
            Search term to filter courses (used by ElasticSearch).
        permissions (list[str]):
            If specified, it filters visible `CourseOverview` objects by
            checking if each permission specified is granted for the username.

    Return value:
        Yield `CourseOverview` objects representing the collection of courses.
    """
    user = get_effective_user(request.user, username)
    course_qs = get_courses(user, org=org, filter_=filter_, permissions=permissions)
    course_qs = _filter_by_search(course_qs, search_term)
    return course_qs
