"""The blocklist view."""

import re
from logging import getLogger

from checkmatelib import CheckmateClient, CheckmateException

LOG = getLogger(__name__)


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    PROXY_PATTERN = re.compile(r"^/proxy/(?:[a-z]{2}_/)?(.*)$")

    def __init__(self, checkmate_host):
        self.checkmate = CheckmateClient(checkmate_host)

    @classmethod
    def get_proxied_url(cls, path):
        """Get the proxied URL from a WSGI environment variable."""

        match = cls.PROXY_PATTERN.match(path)
        if match:
            return match.group(1)

        return None

    def __call__(self, path, environ, start_response):
        """Provide a block page response if required.

        :param path: The url path of the request
        :param environ: WSGI environ dict
        :param start_response: WSGI `start_response()` function
        :return: An iterator of content if required or None
        """
        url = self.get_proxied_url(path)
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
        start_response(
            "307 Temporary Redirect", [("Location", blocked.presentation_url)]
        )
        return []
