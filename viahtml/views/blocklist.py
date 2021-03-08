"""The blocklist view."""

from http import HTTPStatus
from logging import getLogger

from checkmatelib import CheckmateClient, CheckmateException

LOG = getLogger(__name__)


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    def __init__(self, checkmate_host, checkmate_api_key, ignore_reasons=None):
        self.checkmate = CheckmateClient(checkmate_host, checkmate_api_key)
        self._ignore_reasons = ignore_reasons

    def __call__(self, context):
        """Provide a block page response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        url = context.proxied_url
        if not url:
            return None

        blocked_for = context.query_params.get("via.blocked_for")
        try:
            blocked = self.checkmate.check_url(
                url,
                allow_all=True,
                blocked_for=blocked_for,
                ignore_reasons=self._ignore_reasons,
            )
        except CheckmateException as err:
            LOG.warning("Failed to check URL against Checkmate: %s", err)
            return None

        if not blocked:
            return None

        # Redirect the user to the presentation URL given to us by Checkmate

        return context.make_response(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": blocked.presentation_url},
        )
