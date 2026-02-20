import logging
import traceback
from http import HTTPStatus

import sentry_sdk
from checkmatelib import CheckmateException
from sentry_sdk import capture_message

LOG = logging.getLogger(__name__)


class StatusView:
    def __init__(self, checkmate):
        self._checkmate = checkmate

    def __call__(self, context):
        """Provide a status response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        if context.path.rstrip("/") != "/_status":
            # We don't want to handle this call.
            return None

        body = {"status": "okay"}
        http_status = HTTPStatus.OK

        if "include-checkmate" in context.query_params:
            self._check_checkmate(body)

        # If any of the components checked above were down then report the
        # status check as a whole as being down.
        # pylint:disable=redefined-variable-type
        if body.get("down"):
            http_status = HTTPStatus.INTERNAL_SERVER_ERROR
            body["status"] = "down"

        if "sentry" in context.query_params:
            capture_message("Test message from Via HTML's status view")

        return context.make_json_response(
            body,
            http_status=http_status,
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
        )

    def _check_checkmate(self, body):
        with sentry_sdk.start_span(
            op="checkmate.status_check",
            name="Check Checkmate health via check_url",
        ) as span:
            LOG.info("Checking checkmate status via check_url")
            try:
                self._checkmate.check_url("https://example.com/")
            except CheckmateException as exc:
                LOG.error(
                    "Checkmate status check failed: %s: %s\n%s",
                    type(exc).__name__,
                    exc,
                    traceback.format_exc(),
                )
                span.set_status("internal_error")
                span.set_data("error.type", type(exc).__name__)
                span.set_data("error.message", str(exc))
                sentry_sdk.add_breadcrumb(
                    category="checkmate",
                    message=f"Checkmate status check failed: {exc}",
                    level="error",
                    data={
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                )
                sentry_sdk.capture_exception(exc)
                body["down"] = ["checkmate"]
            else:
                LOG.info("Checkmate status check succeeded")
                span.set_status("ok")
                body["okay"] = ["checkmate"]
