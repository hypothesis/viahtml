from functools import partial
from http import HTTPStatus
from unittest.mock import create_autospec, sentinel

import pytest
from checkmatelib import CheckmateClient, CheckmateException
from checkmatelib.client import BlockResponse
from h_matchers import Any

from viahtml.views.security import SecurityView


@pytest.mark.parametrize(
    "referrer",
    [
        None,
        "https://hypothes.is/search",
        "https://example.com",
        # An invalid Referer header. This will cause urlparse to raise.
        "https://example[.com",
        "foo",
    ],
)
@pytest.mark.parametrize(
    "sec_fetch_site", [None, "cross-site", "same-site", "none", "foo"]
)
def test_it_denies_requests_by_default(
    check_url,
    context,
    referrer,
    request_headers,
    sec_fetch_site,
    view_kwargs,
):  # pylint: disable=too-many-arguments
    if referrer:
        request_headers["Referer"] = referrer

    if sec_fetch_site:
        request_headers["Sec-Fetch-Site"] = sec_fetch_site

    response = SecurityView(**view_kwargs)(context)

    check_url.assert_not_called()
    context.make_response.assert_called_once_with(
        HTTPStatus.UNAUTHORIZED,
        lines=Any.list(),
        headers={"Content-Type": "text/html; charset=utf-8"},
    )
    assert response == context.make_response.return_value


@pytest.mark.parametrize("allow_all", [True, False])
def test_if_authentication_is_disabled_it_allows_requests(
    allow_all, check_url, check_url_kwargs, context, view_kwargs
):
    view_kwargs["allow_all"] = allow_all
    view_kwargs["authentication_required"] = False

    response = SecurityView(**view_kwargs)(context)

    check_url_kwargs["allow_all"] = allow_all
    check_url.assert_called_once_with(**check_url_kwargs)
    assert response is None
    assert get_header(context, "X-Via-Authorized-Because") == [
        "Authentication disabled"
    ]


def test_if_debug_mode_is_off_it_doesnt_add_the_x_via_authorized_because_header(
    context, view_kwargs
):
    context.debug = False
    view_kwargs["authentication_required"] = False

    SecurityView(**view_kwargs)(context)

    assert get_header(context, "X-Via-Authorized-Because") == []


@pytest.mark.usefixtures("with_checkmate_blocking_all_urls")
def test_if_authentication_is_disabled_checkmate_blocks_still_apply(
    assert_blocked_by_checkmate, context, view_kwargs
):
    view_kwargs["authentication_required"] = False

    response = SecurityView(**view_kwargs)(context)

    assert_blocked_by_checkmate(response)


@pytest.mark.parametrize("authentication_required", [True, False])
@pytest.mark.parametrize("allow_all", [True, False])
def test_if_sec_fetch_site_is_same_origin_it_allows_requests_and_bypasses_the_allow_list(
    allow_all,
    authentication_required,
    check_url,
    check_url_kwargs,
    context,
    request_headers,
    view_kwargs,
):  # pylint:disable=too-many-arguments
    view_kwargs["allow_all"] = allow_all
    view_kwargs["authentication_required"] = authentication_required

    request_headers["Sec-Fetch-Site"] = "same-origin"

    response = SecurityView(**view_kwargs)(context)

    check_url_kwargs["allow_all"] = True
    check_url.assert_called_once_with(**check_url_kwargs)
    assert response is None
    assert get_header(context, "X-Via-Authorized-Because") == ["Sec-Fetch-Site"]


@pytest.mark.usefixtures("with_checkmate_blocking_all_urls")
def test_if_sec_fetch_site_is_same_origin_checkmate_blocks_still_apply(
    assert_blocked_by_checkmate, context, request_headers, view_kwargs
):
    request_headers["Sec-Fetch-Site"] = "same-origin"

    response = SecurityView(**view_kwargs)(context)

    assert_blocked_by_checkmate(response)


@pytest.mark.parametrize("authentication_required", [True, False])
@pytest.mark.parametrize("allow_all", [True, False])
def test_if_referer_is_same_origin_it_allows_requests_and_bypasses_the_allow_list(
    allow_all,
    authentication_required,
    check_url,
    check_url_kwargs,
    context,
    request_headers,
    view_kwargs,
):  # pylint:disable=too-many-arguments
    view_kwargs["allow_all"] = allow_all
    view_kwargs["authentication_required"] = authentication_required

    request_headers["Referer"] = "https://via.hypothes.is/https://example.com"

    response = SecurityView(**view_kwargs)(context)

    check_url_kwargs["allow_all"] = True
    check_url.assert_called_once_with(**check_url_kwargs)
    assert response is None
    assert get_header(context, "X-Via-Authorized-Because") == ["Same-origin Referer"]


@pytest.mark.usefixtures("with_checkmate_blocking_all_urls")
def test_if_referer_is_same_origin_checkmate_blocks_still_apply(
    assert_blocked_by_checkmate, context, request_headers, view_kwargs
):
    request_headers["Referer"] = "https://via.hypothes.is/https://example.com"

    response = SecurityView(**view_kwargs)(context)

    assert_blocked_by_checkmate(response)


@pytest.mark.parametrize("allow_all", [True, False])
def test_if_Referer_is_in_ALLOWED_REFERRERS_it_allows_the_request_subject_to_the_allow_list(
    allow_all, check_url, check_url_kwargs, context, request_headers, view_kwargs
):  # pylint:disable=too-many-arguments
    request_headers["Referer"] = "https://lms.hypothes.is/lti_launches"
    view_kwargs["allow_all"] = allow_all

    response = SecurityView(**view_kwargs)(context)

    check_url_kwargs["allow_all"] = allow_all
    check_url.assert_called_once_with(**check_url_kwargs)
    assert response is None
    assert get_header(context, "X-Via-Authorized-Because") == ["Allowed Referer"]


@pytest.mark.usefixtures("with_checkmate_blocking_all_urls")
def test_if_Referer_is_in_ALLOWED_REFERRERS_checkmate_blocks_still_apply(
    assert_blocked_by_checkmate, context, request_headers, view_kwargs
):
    request_headers["Referer"] = "https://lms.hypothes.is/lti_launches"

    response = SecurityView(**view_kwargs)(context)

    assert_blocked_by_checkmate(response)


@pytest.mark.usefixtures("with_checkmate_blocking_all_urls")
def test_if_theres_no_proxied_url_it_doesnt_call_checkmate(
    context, request_headers, view_kwargs
):
    context.proxied_url = None
    # Set Sec-Fetch-Site so that the code proceeds to the Checkmate check.
    # This is necessary to get to the code that deals with proxied_url being
    # None.
    request_headers["Sec-Fetch-Site"] = "same-origin"

    response = SecurityView(**view_kwargs)(context)

    assert response is None


@pytest.mark.parametrize("blocked_for", [None, "lms"])
def test_blocked_for_query_param(
    blocked_for, check_url, context, request_headers, view_kwargs
):
    # Set Sec-Fetch-Site so that the code proceeds to the Checkmate check.
    # This is necessary to get to the code that deals with via.blocked_for.
    request_headers["Sec-Fetch-Site"] = "same-origin"

    if blocked_for:
        context.query_params["via.blocked_for"] = blocked_for

    SecurityView(**view_kwargs)(context)

    assert check_url.call_args[1]["blocked_for"] == blocked_for


def test_if_checkmate_crashes_it_allows_the_request(
    check_url, context, request_headers, view_kwargs
):
    check_url.side_effect = CheckmateException
    # Set Sec-Fetch-Site so that the code proceeds to the Checkmate check.
    # This is necessary to get to the code that deals with Checkmate crashes.
    request_headers["Sec-Fetch-Site"] = "same-origin"

    response = SecurityView(**view_kwargs)(context)

    assert response is None


@pytest.fixture
def assert_blocked_by_checkmate(check_url, context):
    """Return a function that asserts that a response is a Checkmate block."""

    def assert_blocked_by_checkmate(response):
        """Assert that `response` is a redirect to a Checkmate block page."""
        context.make_response.assert_called_once_with(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": check_url.return_value.presentation_url},
        )
        assert response == context.make_response.return_value

    return assert_blocked_by_checkmate


@pytest.fixture
def check_url():
    """Return the check_url function will be passed to SecurityView()."""
    checkmate = CheckmateClient(
        "http://checkmate.example.com", sentinel.checkmate_api_key
    )
    check_url = partial(checkmate.check_url, ignore_reasons=sentinel.ignore_reasons)
    return create_autospec(
        check_url,
        return_value=False,  # By default Checkmate allows all URLs.
    )


@pytest.fixture
def check_url_kwargs(context, view_kwargs):
    """Return the kwargs that check_url() should be called with."""
    return {
        "url": context.proxied_url,
        "allow_all": view_kwargs["allow_all"],
        "blocked_for": context.query_params.get("via.blocked_for"),
    }


@pytest.fixture
def context(context, request_headers):
    """Return the Context object for passing to SecurityView.__call__()."""
    context.host = "via.hypothes.is"
    context.proxied_url = "https://example.com/foo"
    context.headers = []
    context.get_header.side_effect = request_headers.get
    context.query_params = {}
    return context


@pytest.fixture
def request_headers():
    """Return the headers that were sent in the test request."""
    return {}


@pytest.fixture
def view_kwargs(check_url):
    """Return a dict of valid kwargs to pass to SecurityView(**view_kwargs)."""
    return {
        "allow_all": False,
        "allowed_referrers": ["lms.hypothes.is"],
        "authentication_required": True,
        "check_url": check_url,
    }


@pytest.fixture
def with_checkmate_blocking_all_urls(check_url):
    """Configure Checkmate to block all URLs."""
    check_url.return_value = create_autospec(
        BlockResponse, instance=True, spec_set=True
    )


def get_header(context, header_name):
    """Return all response header values that've been set for header_name."""
    return [header[1] for header in context.headers if header[0] == header_name]
