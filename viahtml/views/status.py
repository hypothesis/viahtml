from http import HTTPStatus

from checkmatelib import CheckmateException
from sentry_sdk import capture_message


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
            try:
                self._checkmate.check_url("https://example.com/")
            except CheckmateException:
                body["down"] = ["checkmate"]
            else:
                body["okay"] = ["checkmate"]

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
