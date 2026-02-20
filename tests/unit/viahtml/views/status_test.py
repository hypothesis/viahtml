import logging
from unittest.mock import MagicMock, create_autospec

import pytest
from checkmatelib import CheckmateClient, CheckmateException

from viahtml.views.status import StatusView


class TestStatusView:
    @pytest.mark.parametrize(
        "path,responds",
        (
            ("/_status", True),
            ("/_status/", True),
            ("/http://example.com", False),
        ),
    )
    def test_it_responds_to_the_status_url(self, path, responds, context, view):
        context.path = path

        result = view(context)

        if responds:
            context.make_json_response.assert_called_once()
            assert result is not None
        else:
            context.make_json_response.assert_not_called()
            assert result is None

    @pytest.mark.parametrize(
        "checkmate_fails,checkmate_param,expected_body,expected_http_status",
        [
            # With no `checkmate` query param it doesn't check Checkmate.
            (False, False, {"status": "okay"}, 200),
            # With no `checkmate` query param the status endpoint still
            # succeeds even if Checkmate is failing.
            (True, False, {"status": "okay"}, 200),
            # If the `checkmate` query param is given then it checks Checkmate.
            (False, True, {"status": "okay", "okay": ["checkmate"]}, 200),
            # With the `checkmate` query param if Checkmate fails then the
            # status endpoint fails.
            (True, True, {"status": "down", "down": ["checkmate"]}, 500),
        ],
    )
    def test_it(
        self,
        context,
        view,
        checkmate,
        checkmate_fails,
        checkmate_param,
        expected_body,
        expected_http_status,
        capture_message,
    ):  # pylint:disable=too-many-arguments
        if checkmate_fails:
            checkmate.check_url.side_effect = CheckmateException

        if checkmate_param:
            context.query_params = {"include-checkmate": [""]}

        response = view(context)

        if checkmate_param:
            checkmate.check_url.assert_called_once_with("https://example.com/")
        else:
            checkmate.check_url.assert_not_called()
        context.make_json_response.assert_called_once_with(
            expected_body,
            http_status=expected_http_status,
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
        )
        assert response == context.make_json_response.return_value
        capture_message.assert_not_called()

    def test_it_sends_test_messages_to_sentry(self, context, view, capture_message):
        context.query_params = {"sentry": [""]}

        view(context)

        capture_message.assert_called_once_with(
            "Test message from Via HTML's status view"
        )

    def test_it_logs_checkmate_failure_details(
        self, context, view, checkmate, caplog
    ):
        exc = CheckmateException("Connection timed out")
        checkmate.check_url.side_effect = exc
        context.query_params = {"include-checkmate": [""]}

        with caplog.at_level(logging.ERROR, logger="viahtml.views.status"):
            view(context)

        assert any(
            "Checkmate status check failed" in record.message
            and "Connection timed out" in record.message
            for record in caplog.records
        ), f"Expected checkmate failure log, got: {[r.message for r in caplog.records]}"

    def test_it_logs_checkmate_success(self, context, view, caplog):
        context.query_params = {"include-checkmate": [""]}

        with caplog.at_level(logging.INFO, logger="viahtml.views.status"):
            view(context)

        assert any(
            "Checkmate status check succeeded" in record.message
            for record in caplog.records
        ), f"Expected checkmate success log, got: {[r.message for r in caplog.records]}"

    def test_it_creates_sentry_span_on_checkmate_failure(
        self, context, view, checkmate, sentry_start_span, sentry_capture_exception
    ):
        exc = CheckmateException("Connection timed out")
        checkmate.check_url.side_effect = exc
        context.query_params = {"include-checkmate": [""]}

        view(context)

        sentry_start_span.assert_called_once_with(
            op="checkmate.status_check",
            name="Check Checkmate health via check_url",
        )
        span = sentry_start_span.return_value.__enter__.return_value
        span.set_status.assert_called_once_with("internal_error")
        span.set_data.assert_any_call("error.type", "CheckmateException")
        span.set_data.assert_any_call("error.message", "Connection timed out")
        sentry_capture_exception.assert_called_once_with(exc)

    def test_it_creates_sentry_span_on_checkmate_success(
        self, context, view, sentry_start_span, sentry_capture_exception
    ):
        context.query_params = {"include-checkmate": [""]}

        view(context)

        sentry_start_span.assert_called_once_with(
            op="checkmate.status_check",
            name="Check Checkmate health via check_url",
        )
        span = sentry_start_span.return_value.__enter__.return_value
        span.set_status.assert_called_once_with("ok")
        sentry_capture_exception.assert_not_called()

    def test_it_adds_sentry_breadcrumb_on_checkmate_failure(
        self, context, view, checkmate, sentry_add_breadcrumb
    ):
        exc = CheckmateException("Connection timed out")
        checkmate.check_url.side_effect = exc
        context.query_params = {"include-checkmate": [""]}

        view(context)

        sentry_add_breadcrumb.assert_called_once_with(
            category="checkmate",
            message="Checkmate status check failed: Connection timed out",
            level="error",
            data={
                "exception_type": "CheckmateException",
                "exception_message": "Connection timed out",
            },
        )

    @pytest.fixture
    def checkmate(self):
        return create_autospec(CheckmateClient, instance=True, spec_set=True)

    @pytest.fixture
    def context(self, context):
        context.path = "/_status"
        return context

    @pytest.fixture
    def view(self, checkmate):
        return StatusView(checkmate)

    @pytest.fixture(autouse=True)
    def sentry_start_span(self, patch):
        return patch("viahtml.views.status.sentry_sdk.start_span")

    @pytest.fixture(autouse=True)
    def sentry_capture_exception(self, patch):
        return patch("viahtml.views.status.sentry_sdk.capture_exception")

    @pytest.fixture(autouse=True)
    def sentry_add_breadcrumb(self, patch):
        return patch("viahtml.views.status.sentry_sdk.add_breadcrumb")


@pytest.fixture(autouse=True)
def capture_message(patch):
    return patch("viahtml.views.status.capture_message")
