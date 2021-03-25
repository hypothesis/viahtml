"""The status end-point for health checks."""
from logging import getLogger

from checkmatelib import CheckmateClient, CheckmateException

LOG = getLogger(__name__)


class StatusView:
    """Status end-point."""

    def __init__(self, checkmate_host, checkmate_api_key, ignore_reasons=None):
        self._checkmate = CheckmateClient(checkmate_host, checkmate_api_key)
        self._ignore_reasons = ignore_reasons

    def __call__(self, context):
        """Provide a status response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        if context.path.rstrip("/") != "/_status":
            # We don't want to handle this call.
            return None

        status = "okay"

        try:
            self._checkmate.check_url("https://example.com/")
        except CheckmateException:
            status = "checkmate_failure"
            LOG.exception("Checkmate request failed")

        return context.make_json_response(
            {"status": status}, headers={"Cache-Control": "no-cache"}
        )
