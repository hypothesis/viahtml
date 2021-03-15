"""Specific configuration for headers."""
from itertools import takewhile

from werkzeug.datastructures import ResponseCacheControl
from werkzeug.http import parse_cache_control_header


class Headers:
    """Methods for manipulating the headers we accept and emit."""

    CLOUDFLARE_MIN_CACHE_TIME = 30 * 60

    BLOCKED = {
        # h CSRF token header
        "X-Csrf-Token",
    }

    BLOCKED_INBOUND = {
        # Passing CF headers on to via causes "Error 1000: DNS points to
        # prohibited IP" errors at CloudFlare, so we have to strip them out
        # here.
        "Cdn-Loop",
        "Cf-Connecting-Ip",
        "Cf-Ipcountry",
        "Cf-Ray",
        "Cf-Request-Id",
        "Cf-Visitor",
        # AWS headers
        "X-Amzn-Trace-Id",
    } | BLOCKED

    BLOCKED_OUTBOUND = {
        # Disable the Content-Security-Policy which blocks our embed
        "Content-Security-Policy",
        # Various headers added by `pywb` relating to archival
        "Memento-Datetime",
        "Link",
        # We need the Referer header because we use it to authenticate requests
        # (see authentication.py).
        #
        # Sites can use the Referrer-Policy header to tell the browser *not* to
        # send the Referer header (for example: Referrer-Policy: no-referrer).
        # We block Referrer-Policy headers to prevent that.
        "Referrer-Policy",
    } | BLOCKED

    def __init__(self):
        # Headers in the HTTP environ are stored upper case with 'HTTP_' prefix
        self._bad_inbound_environ = {
            self.environ_name(header_name) for header_name in self.BLOCKED_INBOUND
        }

        # Convert to lower case for case-insensitive matching
        self._bad_outbound_lower = {header.lower() for header in self.BLOCKED_OUTBOUND}

    @classmethod
    def environ_name(cls, header_name):
        """Convert a header to the name it has in the WSGI environ.

        :param header_name: Normal header name
        :return: WSGI environ key
        """
        return "HTTP_" + header_name.upper().replace("-", "_")

    def modify_inbound(self, http_env):
        """Modify the headers received by the app.

        This will discard headers we do not want the app to receive.

        :param http_env: WSGI environ dict
        :return: A modified dict
        """
        bad_keys = set(http_env.keys()) & self._bad_inbound_environ

        for bad_key in bad_keys:
            http_env.pop(bad_key)

        return http_env

    def modify_outbound(self, header_items):
        """Modify the headers emitted by the app.

        This will remove headers we do not want to emit.

        :param header_items: Header key-value pairs
        :return: Modified key-value pairs
        """
        headers = []

        for header, value in header_items:
            header_lower = header.lower()
            if header_lower == "x-archive-orig-cache-control":
                headers.append(("Cache-Control", self.translate_cache_control(value)))

            if (
                # Skip any of the many, many headers `pywb` emits
                not header_lower.startswith("x-archive-")
                # Or anything we've blocked explicitly
                and header_lower not in self._bad_outbound_lower
            ):
                headers.append((header, value))

        # Add our own Referrer-Policy telling browsers to send us Referer headers.
        #
        # We need the Referer header because we use it to authenticate requests
        # (see authentication.py).
        #
        # This isn't strictly necessary because we block third-party
        # Referrer-Policy headers in BLOCKED_OUTBOUND above and browsers
        # default referrer policies *do* send the Referer header.
        #
        # But just for good measure (e.g. if some browser settings, extensions,
        # or future browser versions change to *not* sending Referer by
        # default) we inject a header to explicitly ask for Referer.
        headers.append(("Referrer-Policy", "no-referrer-when-downgrade"))

        # Tell Google and other search engines not to index third-party pages
        # proxied by Via HTML and not to follow links on those pages.
        headers.append(("X-Robots-Tag", "noindex, nofollow"))

        return headers

    def translate_cache_control(self, value):
        """Convert a cache-control header to respect Cloudflare limits.

        Where a caching header is marked as public and with a "max-age" below
        the Cloudflare minimum, convert it to "public" caching. This prevents
        Cloudflare from caching things too long but still allows browsers to
        cache.

        :param value: A cache control header value
        :return: A modified cache control value
        """
        parsed = parse_cache_control_header(value, cls=ResponseCacheControl)

        if not parsed.public or parsed.max_age is None:
            return value

        # `parsed.max_age` will be an `int` if the value consists only of digits
        # but a `str` if it contains anything else.
        if isinstance(parsed.max_age, str):
            max_age_digits = "".join(takewhile(str.isdigit, parsed.max_age))
            try:
                parsed.max_age = int(max_age_digits)
            except ValueError:
                # If we couldn't extract a valid `max_age` value, treat it as zero
                # to prevent downstream from caching it in case it was intended to
                # be < CLOUDFLARE_MIN_CACHE_TIME.
                parsed.max_age = 0

        if parsed.max_age < self.CLOUDFLARE_MIN_CACHE_TIME:
            parsed.public = False
            parsed.private = True

        return parsed.to_header()
