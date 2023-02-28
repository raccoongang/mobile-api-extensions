from unittest import mock

import pytest
from pytest_stub.toolbox import stub_global

stub_global(
    {
        "openedx.core.djangoapps.plugins.constants": "[mock]",
    }
)


@pytest.fixture
def json_response():
    _response = mock.Mock()
    _response.status_code = 200
    _response.message = "Valid"

    return _response


@pytest.fixture
def false_json_response():
    _response = mock.Mock()
    _response.status_code = 400

    return _response
