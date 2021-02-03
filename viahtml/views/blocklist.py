"""The blocklist view."""

from http import HTTPStatus
from logging import getLogger

from checkmatelib import CheckmateClient, CheckmateException

LOG = getLogger(__name__)


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    def __init__(self, checkmate_host, checkmate_api_key):
        self.checkmate = CheckmateClient(checkmate_host, checkmate_api_key)

    def __call__(self, context):
        """Provide a block page response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        url = context.proxied_url
        if not url:
            return None

        try:
            blocked = self.checkmate.check_url(url, allow_all=True)
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
