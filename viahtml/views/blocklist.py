"""The blocklist view."""

import logging
from http import HTTPStatus

from checkmatelib import CheckmateException


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    def __init__(self, checkmate, allow_all, ignore_reasons=None):
        """Initialize a new BlocklistView.

        :param checkmate: the Checkmate client object
        :type checkmate: checkmatelib.CheckmateClient

        :param allow_all: whether to bypass Checkmate's allow list
        :type allow_all_: bool

        :param ignore_reasons: comma-separated list of Checkmate
            "detection reasons" to ignore, for example:
            "publisher-blocked,high-io"
        :type ignore_reasons: str
        """
        self._checkmate = checkmate
        self._allow_all = allow_all
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
            blocked = self._checkmate.check_url(
                url,
                allow_all=self._allow_all,
                blocked_for=blocked_for,
                ignore_reasons=self._ignore_reasons,
            )
        except CheckmateException:
            logging.exception("Failed to check URL against Checkmate")
            blocked = None

        if not blocked:
            return None

        # Redirect the user to the presentation URL given to us by Checkmate

        return context.make_response(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": blocked.presentation_url},
        )
