"""
Views for user API
"""
from django.contrib.auth import get_user_model
from edx_rest_framework_extensions.paginators import DefaultPagination
from lms.djangoapps.certificates.api import certificate_downloadable_status
from lms.djangoapps.course_api.blocks.views import BlocksInCourseView
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.discussion.rest_api.api import create_comment
from lms.djangoapps.discussion.rest_api.views import CommentViewSet
from lms.djangoapps.mobile_api.users.views import UserCourseEnrollmentsList
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.accounts.serializers import AccountLegacyProfileSerializer
from rest_framework.response import Response


User = get_user_model()


class UserCourseEnrollmentsListExtended(UserCourseEnrollmentsList):
    """
    **Use Case**

        Get information about the courses that the currently signed in user is
        enrolled in.

        v1 differs from v0.5 version by returning ALL enrollments for
        a user rather than only the enrollments the user has access to (that haven't expired).
        An additional attribute "expiration" has been added to the response, which lists the date
        when access to the course will expire or null if it doesn't expire.

    **Example Request**

        GET /mobile_api_extensions/v1/users/{username}/course_enrollments/

    **Response Values**

        If the request for information about the user is successful, the
        request returns an HTTP 200 "OK" response.

        The HTTP 200 response has the following values.

        * previous: The URL of the previous page of results or null if it is the first page.
        * next: The URL of the next page of results or null if it is the last page.
        * count: Number of course enrollments.
        * current_page: The current page.
        * start: The list index of the first item in the response.
        * results: List of results.
            * expiration: The course expiration date for given user course pair
            or null if the course does not expire.
            * certificate: Information about the user's earned certificate in the
            course.
            * course: A collection of the following data about the course.

            * courseware_access: A JSON representation with access information for the course,
            including any access errors.

            * course_about: The URL to the course about page.
            * course_sharing_utm_parameters: Encoded UTM parameters to be included in course sharing url
            * course_handouts: The URI to get data for course handouts.
            * course_image: The path to the course image.
            * course_updates: The URI to get data for course updates.
            * discussion_url: The URI to access data for course discussions if
                it is enabled, otherwise null.
            * end: The end date of the course.
            * id: The unique ID of the course.
            * name: The name of the course.
            * number: The course number.
            * org: The organization that created the course.
            * start: The date and time when the course starts.
            * start_display:
                If start_type is a string, then the advertised_start date for the course.
                If start_type is a timestamp, then a formatted date for the start of the course.
                If start_type is empty, then the value is None and it indicates that the course has not yet started.
            * start_type: One of either "string", "timestamp", or "empty"
            * subscription_id: A unique "clean" (alphanumeric with '_') ID of
                the course.
            * video_outline: The URI to get the list of all videos that the user
                can access in the course.

            * created: The date the course was created.
            * is_active: Whether the course is currently active. Possible values
            are true or false.
            * mode: The type of certificate registration for this course (honor or
            certified).
            * url: URL to the downloadable version of the certificate, if exists.
    """
    pagination_class = DefaultPagination


class CommentViewSetExtended(CommentViewSet):
    """
    **POST Parameters**:

        * thread_id (required): The thread to post the comment in

        * parent_id: The parent comment of the new comment. Can be null or
          omitted for a comment that should be directly under the thread

        * raw_body: The comment's raw body text

        * anonymous (optional): A boolean indicating whether the comment is
        anonymous; defaults to false

        * anonymous_to_peers (optional): A boolean indicating whether the
        comment is anonymous to peers; defaults to false

    **POST Response Values**:

        * id: The id of the comment

        * thread_id: The id of the comment's thread

        * parent_id: The id of the comment's parent

        * author: The username of the comment's author, or None if the
          comment is anonymous

        * author_label: A label indicating whether the author has a special
          role in the course, either "Staff" for moderators and
          administrators or "Community TA" for community TAs

        * created_at: The ISO 8601 timestamp for the creation of the comment

        * updated_at: The ISO 8601 timestamp for the last modification of
            the comment, which may not have been an update of the body

        * raw_body: The comment's raw body text without any rendering applied

        * endorsed: Boolean indicating whether the comment has been endorsed
            (by a privileged user or, for a question thread, the thread
            author)

        * endorsed_by: The username of the endorsing user, if available

        * endorsed_by_label: A label indicating whether the endorsing user
            has a special role in the course (see author_label)

        * endorsed_at: The ISO 8601 timestamp for the endorsement, if
            available

        * abuse_flagged: Boolean indicating whether the requesting user has
          flagged the comment for abuse

        * abuse_flagged_any_user: Boolean indicating whether any user has
            flagged the comment for abuse. Returns null if requesting user
            is not a moderator.

        * voted: Boolean indicating whether the requesting user has voted
          for the comment

        * vote_count: The number of votes for the comment

        * children: The list of child comments (with the same format)

        * editable_fields: The fields that the requesting user is allowed to
            modify with a PATCH request

        * anonymous: A boolean indicating whether the comment is anonymous

        * anonymous_to_peers: A boolean indicating whether the comment is
        anonymous to peers

        * profile_image: Metadata about a user's profile image
    """

    def create(self, request):
        """
        Implements the POST method for the list endpoint as described in the
        class docstring.
        """
        data = create_comment(request, request.data)
        extended_data = {
            'profile_image': {},
        }

        if hasattr(request.user, 'profile'):
            extended_data.update({
                'profile_image': AccountLegacyProfileSerializer.get_profile_image(
                    request.user.profile, request.user, request)
            })

        data.update(extended_data)
        return Response(data)


class BlocksInCourseViewExtended(BlocksInCourseView):
    """
    **Use Case**

        Returns the blocks in the course according to the requesting user's
        access level.

    **Example requests**:

        GET /api/courses/v1/blocks/?course_id=<course_id>
        GET /api/courses/v1/blocks/?course_id=<course_id>
            &username=anjali
            &depth=all
            &requested_fields=graded,format,student_view_multi_device,lti_url
            &block_counts=video
            &student_view_data=video
            &block_types_filter=problem,html

    **Parameters**:

        This view redirects to /api/courses/v1/blocks/<root_usage_key>/ for the
        root usage key of the course specified by course_id.  The view accepts
        all parameters accepted by :class:`BlocksView`, plus the following
        required parameter

        * course_id: (string, required) The ID of the course whose block data
          we want to return

    **Response Values**

        Responses are identical to those returned by :class:`BlocksView` when
        passed the root_usage_key of the requested course.

        If the course_id is not supplied, a 400: Bad Request is returned, with
        a message indicating that course_id is required.

        If an invalid course_id is supplied, a 400: Bad Request is returned,
        with a message indicating that the course_id is not valid.
    """

    def get_certificate(self, request, user, course_id):
        """Returns the information about the user's certificate in the course."""
        certificate_info = certificate_downloadable_status(user, course_id)
        if certificate_info['is_downloadable']:
            return {
                'url': request.build_absolute_uri(
                    certificate_info['download_url']
                ),
            }
        else:
            return {}

    def list(self, request, hide_access_denials=False):  # pylint: disable=arguments-differ
        """
        Retrieves the usage_key for the requested course, and then returns the
        same information that would be returned by BlocksView.list, called with
        that usage key

        Arguments:
            request - Django request object
        """
        response = super().list(request,
                                hide_access_denials=hide_access_denials)

        course_id = request.query_params.get('course_id', None)
        course_key = CourseKey.from_string(course_id)
        course_overview = CourseOverview.get_from_id(course_key)

        course_data = {
            # identifiers
            'id': course_id,
            'name': course_overview.display_name,
            'number': course_overview.display_number_with_default,
            'org': course_overview.display_org_with_default,

            # dates
            'start': course_overview.start,
            'start_display': course_overview.start_display,
            'start_type': course_overview.start_type,
            'end': course_overview.end,

            # access info
            'courseware_access': has_access(
                request.user,
                'load_mobile',
                course_overview
            ).to_json(),

            # various URLs
            'media': {
                'image': course_overview.image_urls,
            },
            'certificate': self.get_certificate(request, request.user, course_key),
            'is_self_paced': course_overview.self_paced
        }

        response.data.update(course_data)
        return response
