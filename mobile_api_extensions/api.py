"""
Views for user API
"""
from common.djangoapps.student.models import CourseEnrollment
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from edx_rest_framework_extensions.paginators import DefaultPagination
from lms.djangoapps.certificates.api import certificate_downloadable_status
from lms.djangoapps.course_api.blocks.views import BlocksInCourseView
from lms.djangoapps.course_api.views import CourseDetailView, CourseListView
from lms.djangoapps.course_api.forms import CourseListGetForm
from lms.djangoapps.courseware.access import has_access
from lms.djangoapps.courseware.courses import get_course_with_access
from lms.djangoapps.discussion.rest_api.views import CommentViewSet
from lms.djangoapps.grades.course_grade_factory import CourseGradeFactory
from lms.djangoapps.mobile_api.users.views import UserCourseEnrollmentsList
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
from openedx.core.djangoapps.user_api.accounts.serializers import AccountLegacyProfileSerializer
from openedx.core.djangoapps.user_api.accounts.views import DeactivateLogoutView
from openedx.core.lib.api.authentication import BearerAuthentication
from openedx.core.lib.api.view_utils import view_auth_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from .utils import list_courses


User = get_user_model()


@view_auth_classes()
class CourseProgressView(APIView):

    def get(self, request, course_id):
        course_key = CourseKey.from_string(course_id)
        course = get_course_with_access(request.user, 'load', course_key)

        course_grade = CourseGradeFactory().read(request.user, course)
        courseware_summary = course_grade.chapter_grades.values()

        progress_data = []

        staff_access = bool(has_access(request.user, 'staff', course))

        for chapter in courseware_summary:
            chapter_data = {
                'display_name': chapter['display_name'],
                'subsections': []
            }

            for section in chapter['sections']:
                earned = section.all_total.earned
                total = section.all_total.possible
                section_data = dict(
                    earned=earned,
                    total=total,
                    percentageString="{0:.0%}".format(section.percent_graded),
                    display_name=section.display_name,
                    score=[{'earned': score.earned, 'possible': score.possible} for score in section.problem_scores.values()],
                    show_grades=section.show_grades(staff_access),
                    graded=section.graded,
                    grade_type=section.format or '',
                )
                chapter_data['subsections'].append(section_data)

            progress_data.append(chapter_data)
        return Response({'sections': progress_data})


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
    **Example Requests**:

        POST /mobile_api_extensions/discussion/v1/comments/
        {
            "thread_id": "0123456789abcdef01234567",
            "raw_body": "Body text"
        }

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
        response = super().create(request)
        extended_data = {
            'profile_image': {},
        }

        if hasattr(request.user, 'profile'):
            extended_data.update({
                'profile_image': AccountLegacyProfileSerializer.get_profile_image(
                    request.user.profile, request.user, request)
            })

        response.data.update(extended_data)
        return response


class BlocksInCourseViewExtended(BlocksInCourseView):
    """
    **Use Case**

        Returns the blocks in the course according to the requesting user's
        access level.

    **Example requests**:

        GET /mobile_api_extensions/v1/blocks/?course_id=<course_id>
        GET /mobile_api_extensions/v1/blocks/?course_id=<course_id>
            &username=anjali
            &depth=all
            &requested_fields=graded,format,student_view_multi_device,lti_url
            &block_counts=video
            &student_view_data=video
            &block_types_filter=problem,html

    **Parameters**:

        This view redirects to /mobile_api_extensions/v1/blocks/<root_usage_key>/ for the
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


class CourseDetailViewExtended(CourseDetailView):
    """
    **Use Cases**

        Request details for a course

    **Example Requests**

        GET /mobile_api_extensions/v1/courses/{course_key}/

    **Response Values**

        Body consists of the following fields:

        * effort: A textual description of the weekly hours of effort expected
            in the course.
        * end: Date the course ends, in ISO 8601 notation
        * enrollment_end: Date enrollment ends, in ISO 8601 notation
        * enrollment_start: Date enrollment begins, in ISO 8601 notation
        * id: A unique identifier of the course; a serialized representation
            of the opaque key identifying the course.
        * media: An object that contains named media items.  Included here:
            * course_image: An image to show for the course.  Represented
            as an object with the following fields:
                * uri: The location of the image
        * name: Name of the course
        * number: Catalog number of the course
        * org: Name of the organization that owns the course
        * overview: A possibly verbose HTML textual description of the course.
            Note: this field is only included in the Course Detail view, not
            the Course List view.
        * short_description: A textual description of the course
        * start: Date the course begins, in ISO 8601 notation
        * start_display: Readably formatted start of the course
        * start_type: Hint describing how `start_display` is set. One of:
            * `"string"`: manually set by the course author
            * `"timestamp"`: generated from the `start` timestamp
            * `"empty"`: no start date is specified
        * pacing: Course pacing. Possible values: instructor, self
        * is_enrolled: A boolean indicating whether the user enrolled in a course.

        Deprecated fields:

        * blocks_url: Used to fetch the course blocks
        * course_id: Course key (use 'id' instead)

    **Parameters:**

        username (optional):
            The username of the specified user for whom the course data
            is being accessed. The username is not only required if the API is
            requested by an Anonymous user.

    **Returns**

        * 200 on success with above fields.
        * 400 if an invalid parameter was sent or the username was not provided
        for an authenticated request.
        * 403 if a user who does not have permission to masquerade as
        another user specifies a username other than their own.
        * 404 if the course is not available or cannot be seen.

        Example response:

            {
                "blocks_url": "/api/courses/v1/blocks/?course_id=edX%2Fexample%2F2012_Fall",
                "media": {
                    "course_image": {
                        "uri": "/c4x/edX/example/asset/just_a_test.jpg",
                        "name": "Course Image"
                    }
                },
                "description": "An example course.",
                "end": "2015-09-19T18:00:00Z",
                "enrollment_end": "2015-07-15T00:00:00Z",
                "enrollment_start": "2015-06-15T00:00:00Z",
                "course_id": "edX/example/2012_Fall",
                "name": "Example Course",
                "number": "example",
                "org": "edX",
                "overview: "<p>A verbose description of the course.</p>"
                "start": "2015-07-17T12:00:00Z",
                "start_display": "July 17, 2015",
                "start_type": "timestamp",
                "pacing": "instructor"
                "is_enrolled": true
            }
    """

    def get(self, request, course_key_string):
        response = super().get(request, course_key_string)
        response.data['is_enrolled'] = CourseEnrollment.is_enrolled(request.user, course_key_string)
        return response


class DeactivateLogoutViewExtended(DeactivateLogoutView):
    """
    POST /mobile_api_extensions/user/v1/accounts/deactivate_logout/
    {
        "password": "example_password",
    }

    **POST Parameters**

      A POST request must include the following parameter.

      * password: Required. The current password of the user being deactivated.

    **POST Response Values**

     If the request does not specify a username or submits a username
     for a non-existent user, the request returns an HTTP 404 "Not Found"
     response.

     If a user who is not a superuser tries to deactivate a user,
     the request returns an HTTP 403 "Forbidden" response.

     If the specified user is successfully deactivated, the request
     returns an HTTP 204 "No Content" response.

     If an unanticipated error occurs, the request returns an
     HTTP 500 "Internal Server Error" response.

    Allows an LMS user to take the following actions:
    -  Change the user's password permanently to Django's unusable password
    -  Log the user out
    - Create a row in the retirement table for that user
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication, BearerAuthentication,)


@view_auth_classes(is_authenticated=False)
class CourseListViewExtended(CourseListView):
    """
    **Use Cases**

        Request information on all courses visible to the specified user.

    **Example Requests**

        GET /mobile_api_extensions/courses/v1/courses/

    **Response Values**

        Body comprises a list of objects as returned by `CourseDetailView`.

    **Parameters**

        search_term (optional):
            Search term to filter courses (used by ElasticSearch).

        username (optional):
            The username of the specified user whose visible courses we
            want to see. The username is not required only if the API is
            requested by an Anonymous user.

        org (optional):
            If specified, visible `CourseOverview` objects are filtered
            such that only those belonging to the organization with the
            provided org code (e.g., "HarvardX") are returned.
            Case-insensitive.

        permissions (optional):
            If specified, it filters visible `CourseOverview` objects by
            checking if each permission specified is granted for the username.
            Notice that Staff users are always granted permission to list any
            course.

    **Returns**

        * 200 on success, with a list of course discovery objects as returned
          by `CourseDetailView`.
        * 400 if an invalid parameter was sent or the username was not provided
          for an authenticated request.
        * 403 if a user who does not have permission to masquerade as
          another user specifies a username other than their own.
        * 404 if the specified user does not exist, or the requesting user does
          not have permission to view their courses.

        Example response:

            [
              {
                "blocks_url": "/api/courses/v1/blocks/?course_id=edX%2Fexample%2F2012_Fall",
                "media": {
                  "course_image": {
                    "uri": "/c4x/edX/example/asset/just_a_test.jpg",
                    "name": "Course Image"
                  }
                },
                "description": "An example course.",
                "end": "2015-09-19T18:00:00Z",
                "enrollment_end": "2015-07-15T00:00:00Z",
                "enrollment_start": "2015-06-15T00:00:00Z",
                "course_id": "edX/example/2012_Fall",
                "name": "Example Course",
                "number": "example",
                "org": "edX",
                "start": "2015-07-17T12:00:00Z",
                "start_display": "July 17, 2015",
                "start_type": "timestamp"
              }
            ]
    """

    def get_queryset(self):
        """
        Yield courses visible to the user.
        """
        form = CourseListGetForm(self.request.query_params, initial={'requesting_user': self.request.user})
        if not form.is_valid():
            raise ValidationError(form.errors)
        return list_courses(
            self.request,
            form.cleaned_data['username'],
            org=form.cleaned_data['org'],
            filter_=form.cleaned_data['filter_'],
            search_term=form.cleaned_data['search_term'],
            permissions=form.cleaned_data['permissions']
        )
