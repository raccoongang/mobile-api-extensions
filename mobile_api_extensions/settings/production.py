"""
Production Django settings for mobile_api_extensions project.
"""

from __future__ import unicode_literals


# pylint: disable=unnecessary-pass,unused-argument
def plugin_settings(settings):
    """
    Set of plugin settings used by the Open Edx platform.
    More info: https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/plugins/README.rst
    """

    settings.MOBILE_SSO_DEEPLINK = settings.ENV_TOKENS.get(
        'MOBILE_SSO_DEEPLINK', settings.MOBILE_SSO_DEEPLINK
    )
