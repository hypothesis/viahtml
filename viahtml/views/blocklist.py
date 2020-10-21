"""The blocklist view."""

import os
import re

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pkg_resources import resource_filename
from werkzeug.wsgi import get_path_info

from viahtml.blocklist import Blocklist


class BlocklistView:
    """A view which checks for blocked pages and returns a blocked page."""

    PROXY_PATTERN = re.compile(r"^/proxy/(?:[a-z]{2}_/)?(.*)$")

    JINJA_ENV = Environment(
        loader=FileSystemLoader(
            os.path.abspath(resource_filename("viahtml", "templates"))
        ),
        autoescape=select_autoescape(["html", "xml"]),
    )

    def __init__(self, file_name):
        self.blocklist = Blocklist(file_name)

    @classmethod
    def get_proxied_url(cls, environ):
        """Get the proxied URL from a WSGI environment variable."""
        path = get_path_info(environ)

        match = cls.PROXY_PATTERN.match(path)
        if match:
            return match.group(1)

        return None

    def __call__(self, environ, start_response):
        """Provide a block page response if required.

        :param environ: WSGI environ dict
        :param start_response: WSGI `start_response()` function
        :return: An iterator of content if required or None
        """
        url = self.get_proxied_url(environ)
        if not url:
            return None

        reason = self.blocklist.is_blocked(url)
        if not reason:
            return None

        start_response("403 Forbidden", [("Content-Type", "text/html; charset=utf-8")])

        template = self.JINJA_ENV.get_template("viahtml/blocked_page.html.jinja2")
        content = template.render(reason=reason, url_to_annotate=url)
        return [content.encode("utf-8")]
