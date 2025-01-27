import logging

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from oauthlib.oauth2.rfc6749.tokens import BearerToken
from oauth2_provider.settings import oauth2_settings
from social_django.utils import psa
from social_django.views import _do_login
from social_core.actions import do_complete as social_core_do_complete, do_auth
from social_core.utils import (
    partial_pipeline_data,
    setting_name,
    setting_url,
    user_is_active,
    user_is_authenticated,
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from common.djangoapps.student.models import UserProfile
from common.djangoapps.student.views import compose_and_send_activation_email
from common.djangoapps.third_party_auth import pipeline, provider
from openedx.core.djangoapps.oauth_dispatch import adapters

from .models import ExtraUserInfo
from .forms import AuthorizationCodeExchangeForm

log = logging.getLogger(__name__)

URL_NAMESPACE = getattr(settings, setting_name('URL_NAMESPACE'), None) or 'social'
MOBILE_ERROR_MSG = "error"
MOBILE_SUCCESS_MSG = "success"


# pylint: disable=unused-variable,unused-argument,logging-fstring-interpolation
def _populate_authorization_code(user):
    """
    Store user's mobile authorization token in a `UserProfile` obj.

    Arguments:
        user (`django.contrib.auth.models.User` obj): edX user object.
    """

    token = None

    if user:
        extrauserinfo, created = ExtraUserInfo.objects.get_or_create(user=user)
        token = extrauserinfo.set_authorization_code()

    return token


def _send_activation_email(user, request):
    """
    Send activation email for non active users.

    Arguments:
        user (`django.contrib.auth.models.User` obj): edX user object.
        request (HTTPRequest)
    """

    try:
        profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        log.exception(f'Could not find UserProfile for {user}')
    else:
        activated = user_is_active(user)
        running_pipeline = pipeline.get(request)
        current_provider = provider.Registry.get_from_pipeline(running_pipeline)
        if current_provider.skip_email_verification and not activated:
            user.is_active = True
            user.save()
            activated = True
        if not activated:
            compose_and_send_activation_email(user, profile)


def mobile_do_complete(backend, login, user=None, redirect_name='next',  # pylint: disable=keyword-arg-before-vararg
                       *args, **kwargs):
    """
    Override social_core's do_complete.

    Add custom logic for mobile apps.
    """
    is_authenticated = user_is_authenticated(user)
    user = user if is_authenticated else None
    mobile_auth_code = ""

    partial = partial_pipeline_data(backend, user, *args, **kwargs)
    if partial:
        user = backend.continue_pipeline(partial)
    else:
        user = backend.complete(user=user, *args, **kwargs)

    # check if the output value is something else than a user and just
    # return it to the client
    user_model = backend.strategy.storage.user.user_model()
    if user and not isinstance(user, user_model):
        return user

    if is_authenticated:
        mobile_auth_code = _populate_authorization_code(user)
    elif user:
        # allow login for non active users
        # catch is_new/social_user in case login() resets the instance
        social_user = user.social_user
        login(backend, user, social_user)

        backend.strategy.session_set('social_auth_last_login_backend',
                                     social_user.provider)

        mobile_auth_code = _populate_authorization_code(user)
        _send_activation_email(user, kwargs['request'])
    else:
        url = setting_url(backend, 'LOGIN_ERROR_URL', 'LOGIN_URL')

    mobile_status_message = (MOBILE_SUCCESS_MSG if mobile_auth_code
                             else MOBILE_ERROR_MSG)

    if mobile_auth_code:
        url = reverse('sso-deeplink')
    url += (('&' if '?' in url else '?') + f'AuthorizationCode={mobile_auth_code}&Status={mobile_status_message}')

    return backend.strategy.redirect(url)


@csrf_exempt
@psa(f'{URL_NAMESPACE}:complete')
def complete_mobile(request, backend, *args, **kwargs):
    """
    Complete authentication social django view override.

    Redirect to mobile deeplink based on custom parameter stored in session.
    """
    backend = request.backend
    redirect_value = backend.strategy.session_get('deeplink_redirect')

    if redirect_value:
        do_complete_view = mobile_do_complete
    else:
        do_complete_view = social_core_do_complete
    return do_complete_view(backend, _do_login, user=request.user,
                            redirect_name=REDIRECT_FIELD_NAME, request=request,
                            *args, **kwargs)


@psa(f'{URL_NAMESPACE}:complete')
def auth_mobile(request, backend):
    """
    Login authentication social django view override.

    Set custom condition for mobile redirect to session.
    """
    redirect_value = request.backend.strategy.request_data().get(REDIRECT_FIELD_NAME, '')
    request.backend.strategy.session_set('deeplink_redirect',
                                         (redirect_value == settings.MOBILE_SSO_DEEPLINK))

    return do_auth(request.backend, redirect_name=REDIRECT_FIELD_NAME)


class AuthorizationCodeExchangeView(APIView):
    """
    Exchange Authorization code for access token.

    Used for mobile apps through DOT backend.

    Supported methods: POST

    Request parameters:
        - client_id (str): Django oauth toolkit Application id
        - authorization_code (str): authorization code recieved by user after successfull
        SAML authorization through SSO for mobile client
    """
    http_method_names = ['post']
    dot_adapter = adapters.DOTAdapter()

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Exchange Authorization code for access token.
        """
        form = AuthorizationCodeExchangeForm(request=request, oauth2_adapter=self.dot_adapter, data=request.POST)

        if not form.is_valid():
            return self.error_response(form.errors)

        user = form.cleaned_data["user"]
        authorization_code = form.cleaned_data["authorization_code"]
        client = form.cleaned_data["client"]
        token = self.create_access_token(request, user, client)
        self._clean_authorization_code(authorization_code)
        return self.access_token_response(token)

    def create_access_token(self, request, user, client):
        """
        Create and return a new access token.
        """
        _days = 24 * 60 * 60
        token_generator = BearerToken(
            expires_in=settings.OAUTH_EXPIRE_PUBLIC_CLIENT_DAYS * _days,
            request_validator=oauth2_settings.OAUTH2_VALIDATOR_CLASS(),
        )
        self._populate_create_access_token_request(request, user, client)
        return token_generator.create_token(request, refresh_token=True)

    def access_token_response(self, token):
        """
        Wrap an access token in an appropriate response
        """
        return Response(data=token)

    def _populate_create_access_token_request(self, request, user, client):
        """
        django-oauth-toolkit expects certain non-standard attributes to
        be present on the request object.  This function modifies the
        request object to match these expectations
        """
        request.user = user
        request.scopes = [scope for scope in settings.OAUTH2_DEFAULT_SCOPES]  # noqa: E501, pylint: disable=unnecessary-comprehension
        request.client = client
        request.state = None
        request.refresh_token = None
        request.extra_credentials = None
        request.grant_type = client.authorization_grant_type

    def _clean_authorization_code(self, authorization_code):
        """
        Set requested authorization_code to None

        Args:
            authorization_code (str): UserProfile.authorization_code
        """
        user = User.objects.get(extra_user_info__authorization_code=authorization_code)
        user.extra_user_info.authorization_code = None
        user.save()

    def error_response(self, form_errors, **kwargs):
        """
        Return an error response consisting of the errors in the form
        """
        return Response(status=400, data=form_errors, **kwargs)


@api_view(["GET"])
def redirect_to_mobile_deeplink(request):
    """Redirect to mobile app SSO endpoint."""
    redirect_url = settings.MOBILE_SSO_DEEPLINK
    redirect_url += f"?AuthorizationCode={request.GET.get('AuthorizationCode')}&Status={request.GET.get('Status')}"
    response = HttpResponse(redirect_url, status=302)
    response['Location'] = redirect_url
    return response


def redirect_to_mobile(request, backend_name):
    """Redirect to SSO login endpoint with next params."""
    extra_params = {
        REDIRECT_FIELD_NAME: settings.MOBILE_SSO_DEEPLINK,
    }

    if backend_name == 'tpa-saml':
        extra_params.update({
            "auth_entry": "login",
            "idp": request.GET.get("idp", "default")
        })

    redirect_url = pipeline._get_url(  # pylint: disable=protected-access
        'social_login_override',
        backend_name,
        extra_params=extra_params
    )
    return redirect(redirect_url)

