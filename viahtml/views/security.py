import logging
from http import HTTPStatus
from urllib.parse import urlparse

from checkmatelib import BadURL, CheckmateException


class SecurityView:
    def __init__(
        self, allow_all, allowed_referrers, authentication_required, check_url
    ):
        self._allow_all = allow_all
        self._allowed_referrers = allowed_referrers
        self._authentication_required = authentication_required
        self._check_url = check_url

    def __call__(self, context):
        authorization_reason, allow_all = self._is_authorized(context)

        if not authorization_reason:
            return context.make_response(
                HTTPStatus.UNAUTHORIZED,
                lines=[self._error_template("Untrusted origin")],
                headers={"Content-Type": "text/html; charset=utf-8"},
            )

        if context.debug:
            context.headers.append(("X-Via-Authorized-Because", authorization_reason))

        try:
            blocked = self._is_blocked(
                context.proxied_url,
                context.query_params.get("via.blocked_for"),
                allow_all,
            )
        except BadURL as exc:
            return context.make_response(
                HTTPStatus.BAD_REQUEST,
                lines=[self._error_template(f"Bad URL: {exc}: {context.proxied_url}")],
                headers={"Content-Type": "text/html; charset=utf-8"},
            )

        if blocked:
            return context.make_response(
                HTTPStatus.TEMPORARY_REDIRECT,
                headers={"Location": blocked.presentation_url},
            )

        return None

    def _is_authorized(self, context):
        """Decide whether or not the request should be authorized.

        Return an (authorization_reason, allow_all) tuple where:

        * authorization_reason is a string saying why the request is authorized.
          For example authorization_reason is "Sec-Fetch-Site" if the request
          is authorized because it has a `Sec-Fetch-Site: same-origin` header.

          authorization_reason is False if the request isn't authorized.

        * allow_all is a boolean saying whether the request should bypass
          Checkmate's allow-list
        """
        allow_all = self._allow_all
        parsed_referrer = self._parsed_referrer(context)

        if self._sec_fetch_site_is_same_origin(context):
            authorization_reason = "Sec-Fetch-Site"
            # This is a subresource request so bypass Checkmate's allow-list
            # regardless of the CHECKMATE_ALLOW_ALL setting.
            allow_all = True
        elif self._is_same_origin(parsed_referrer, context):
            authorization_reason = "Same-origin Referer"
            # This is a subresource request so bypass Checkmate's allow-list
            # regardless of the CHECKMATE_ALLOW_ALL setting.
            allow_all = True
        elif not self._authentication_required:
            authorization_reason = "Authentication disabled"
        elif self._is_allowed(parsed_referrer, self._allowed_referrers):
            authorization_reason = "Allowed Referer"
        else:
            authorization_reason = False

        return authorization_reason, allow_all

    @staticmethod
    def _sec_fetch_site_is_same_origin(context):
        """Return True if the request has Sec-Fetch-Site: same-origin."""
        # The Sec-Fetch-Site header is set in some browsers (eg. Chrome) to
        # indicate where a request came from without divulging the actual
        # origin.
        #
        # Testing this header in addition to Referer is needed because Chrome
        # does not set the Referer in some subresource requests. See
        # https://github.com/hypothesis/viahtml/issues/70.
        return context.get_header("Sec-Fetch-Site") == "same-origin"

    @staticmethod
    def _parsed_referrer(context):
        """Return a parsed copy of the request's Referer header value.

        Return False if the request has no Referer header or has an unparseable
        Referer header value.

        :rytpe: urlparse 6-tuple or False
        """
        referrer = context.get_header("Referer")

        if not referrer:
            return False

        try:
            return urlparse(referrer)
        except ValueError:
            return False

    @staticmethod
    def _is_same_origin(parsed_referrer, context):
        """Return True if parsed_referrer refers to Via iself."""
        return getattr(parsed_referrer, "netloc", None) == context.host

    @staticmethod
    def _is_allowed(parsed_referrer, allowed_referrers):
        """Return True if parsed_referrer is in the allowed_referrers list."""
        return getattr(parsed_referrer, "netloc", None) in allowed_referrers

    def _is_blocked(self, url, blocked_for, allow_all):
        """Return a BlockResponse if the requested URL is blocked by Checkmate.

        :rtype: checkmate.client.BlockResponse, or False if the URL isn't
            blocked

        :raises BadURL: For malformed or private URLs
        """
        if not url:
            return False

        try:
            return self._check_url(
                url=url, allow_all=allow_all, blocked_for=blocked_for
            )
        except BadURL:
            raise
        except CheckmateException:
            logging.exception("Failed to check URL against Checkmate")
            return False

    @staticmethod
    def _error_template(exception):
        # We add a fake favicon here, to prevent the browser from requesting
        # one, as this can trigger `pywb` to issue a redirect which effectively
        # logs the user in by setting a `via.sec` cookie in the response.

        return f"""
        <html>
            <head>
                <link rel="icon" href="data:,">
            </head>
            <body>
                <h1>401 Unauthorized</h1>
                <p>{exception}</p>
            </body>
        </html>
        """
