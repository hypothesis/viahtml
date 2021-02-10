"""A central request context object to cut down on repetition."""

import json
import re
from functools import lru_cache
from http import HTTPStatus

from h_vialib import Configuration
from werkzeug import wsgi


class Context:
    """A request context object."""

    headers = None
    """A list of tuples of headers to add to the request."""

    http_environ = None
    """The WSGI http environ if you need it."""

    start_response = None
    """The start response function if you need it."""

    def __init__(self, http_environ, start_response):
        """Initialize a new context object.

        :param http_environ: WSGI HTTP environment
        :param start_response: WSGI start_response function
        """
        self.http_environ = http_environ
        self.start_response = start_response

        self.headers = []

    @property
    @lru_cache(1)
    def path(self):
        """Get the path in the app (without query parameters)."""
        return wsgi.get_path_info(self.http_environ)

    @property
    @lru_cache(1)
    def url(self):
        """Get the full request URL made to the app (with query params)."""

        return wsgi.get_current_url(self.http_environ)

    @property
    @lru_cache(1)
    def proxied_url(self):
        """Get the proxied URL without any Via parameters."""
        url = self.proxied_url_with_config
        if not url:
            return url

        return Configuration.strip_from_url(url)

    _PROXY_PATTERN = re.compile(r"^proxy/(?:[a-z]{2}_/)?")

    @property
    @lru_cache(1)
    def proxied_url_with_config(self):
        """Get the proxied URL including any Via parameters."""

        app_root = wsgi.get_current_url(self.http_environ, root_only=True)

        url = self.url[len(app_root) :]
        url = self._PROXY_PATTERN.sub("", url)

        # This is a root with query params, not something we can proxy
        if url.startswith("?"):
            return None

        return url if url else None

    def make_response(self, http_status=HTTPStatus.OK, headers=None, lines=None):
        """Create a WSGI response.

        :param http_status: HTTPStatus instance to return
        :param headers: A dict of headers
        :param lines: Lines of text to return
        :return: A correctly formatted series of lines for WSGI response
        """
        if headers:
            for key, value in headers.items():
                self.add_header(key, value)

        lines = [] if lines is None else [line.encode("utf-8") for line in lines]

        status_line = f"{http_status.value} {http_status.phrase}"
        self.start_response(status_line, self.headers)

        return lines

    def make_json_response(self, body, http_status=HTTPStatus.OK, headers=None):
        """Create a JSON WSGI response.

        :param body: Data to return in the JSON body
        :param http_status: HTTPStatus instance to return
        :param headers: A dict of headers
        :return: A correctly formatted series of lines for WSGI response
        """
        if headers is None:
            headers = {}
        headers.setdefault("Content-Type", "application/json; charset=utf-8")

        return self.make_response(
            http_status=http_status, headers=headers, lines=[json.dumps(body)]
        )

    def add_header(self, name, value):
        """Add a header to be added to any responses created."""

        self.headers.append((name, value))

    def get_header(self, name):
        """Get a specific header by name.

        This will search the headers added to the context first, and the HTTP
        environ second.

        :param name: Header name to find
        :return: Value of the first matching header (or None)
        """
        for key, value in self.headers:
            if key.lower() == name.lower():
                return value  #

        # https://tools.ietf.org/html/rfc3875#section-4.1.18
        cgi_name = "HTTP_" + name.upper().replace("-", "")
        return self.http_environ.get(cgi_name)
