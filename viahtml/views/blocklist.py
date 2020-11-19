"""The blocklist view."""

import os
import re
from logging import getLogger

from checkmatelib import CheckmateClient, CheckmateException
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pkg_resources import resource_filename

LOG = getLogger(__name__)


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    PROXY_PATTERN = re.compile(r"^/proxy/(?:[a-z]{2}_/)?(.*)$")

    JINJA_ENV = Environment(
        loader=FileSystemLoader(
            os.path.abspath(resource_filename("viahtml", "templates"))
        ),
        autoescape=select_autoescape(["html", "xml"]),
    )

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
            hits = self.checkmate.check_url(url)
        except CheckmateException as err:
            LOG.warning("Failed to check URL against Checkmate: %s", err)
            return None

        if not hits:
            return None

        start_response("403 Forbidden", [("Content-Type", "text/html; charset=utf-8")])

        template = self.JINJA_ENV.get_template("viahtml/blocked_page.html.jinja2")
        content = template.render(reason=hits.reason_codes[0], url_to_annotate=url)
        return [content.encode("utf-8")]
