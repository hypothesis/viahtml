import functools
from unittest import mock
from unittest.mock import create_autospec

import pytest

from tests.conftest import environment_variables
from viahtml.context import Context


def _autopatcher(request, target, **kwargs):
    """Patch and cleanup automatically. Wraps :py:func:`mock.patch`."""
    options = {"autospec": True}
    options.update(kwargs)
    patcher = mock.patch(target, **options)
    obj = patcher.start()
    request.addfinalizer(patcher.stop)
    return obj


@pytest.fixture
def patch(request):
    return functools.partial(_autopatcher, request)


@pytest.fixture
def os():
    with mock.patch("viahtml.app.os", autospec=True) as os:
        os.environ = environment_variables()
        yield os


@pytest.fixture
def start_response():
    return create_autospec(lambda status, headers: None)  # pragma: no cover


@pytest.fixture
def context(start_response):
    return create_autospec(
        Context, instance=True, spec_set=True, debug=True, start_response=start_response
    )
