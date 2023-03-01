"""
Views for user API
"""

from edx_rest_framework_extensions.paginators import DefaultPagination
from lms.djangoapps.mobile_api.users.views import UserCourseEnrollmentsList


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
