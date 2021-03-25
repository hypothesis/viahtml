"""The status end-point for health checks."""
from logging import getLogger

from checkmatelib import CheckmateException

LOG = getLogger(__name__)


class StatusView:
    """Status end-point."""

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

        status = "okay"

        try:
            self._checkmate.check_url("https://example.com/")
        except CheckmateException:
            status = "checkmate_failure"
            LOG.exception("Checkmate request failed")

        return context.make_json_response(
            {"status": status},
            headers={"Cache-Control": "max-age=0, must-revalidate, no-cache, no-store"},
        )
