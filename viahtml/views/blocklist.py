"""The blocklist view."""

from http import HTTPStatus

from checkmatelib import CheckmateException


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    def __init__(self, checkmate, ignore_reasons=None):
        self._checkmate = checkmate
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
                allow_all=True,
                blocked_for=blocked_for,
                ignore_reasons=self._ignore_reasons,
            )
        except CheckmateException:
            blocked = None

        if not blocked:
            return None

        # Redirect the user to the presentation URL given to us by Checkmate

        return context.make_response(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": blocked.presentation_url},
        )
