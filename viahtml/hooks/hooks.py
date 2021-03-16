"""The majority of configuration options."""
from h_vialib import Configuration

from viahtml.hooks._headers import Headers


class Hooks:
    """A collection of configuration points for `pywb`."""

    headers = Headers()

    def __init__(self, config):
        self.config = config
        self.context = None

    def set_context(self, context):
        """Set the request context for access in hook points."""

        self.context = context

    @property
    def template_vars(self):
        """Get variables to make available in the global Jinja2 environment."""

        def external_link_mode(http_env):
            via_config, _ = self.get_config(http_env)
            return via_config.get("external_link_mode", "same-tab").lower()

        return {
            # It would be much nicer to calculate this once somehow
            "client_params": lambda http_env: self.get_config(http_env)[1],
            "external_link_mode": external_link_mode,
            "ignore_prefixes": self.ignore_prefixes,
            "h_embed_url": self.config["h_embed_url"],
        }

    @property
    def ignore_prefixes(self):
        """Get the list of URL prefixes to ignore (server and client side)."""

        return self.config["ignore_prefixes"]

    @classmethod
    def get_config(cls, http_env):
        """Return the h-client parameters from a WSGI environment."""

        return Configuration.extract_from_wsgi_environment(http_env)

    _REDIRECTS = ("301", "302", "303", "305", "307", "308")

    def modify_render_response(self, response):
        """Return a potentially modified response from pywb.

        :param response: WbResponse object returned from pywb
        :returns: Either the same or a modified response object
        """
        # `status_headers` is an instance of
        # `warcio.statusandheaders.StatusAndHeaders`
        status_code = response.status_headers.get_statuscode()

        if status_code in self._REDIRECTS:
            # Make sure redirects pass on our config
            location = response.status_headers.get_header("Location")
            if location:
                location = self.context.make_absolute(location)

                via_params, client_params = Configuration.extract_from_wsgi_environment(
                    self.context.http_environ, add_defaults=False
                )
                if via_params or client_params:
                    location = Configuration.add_to_url(
                        location, via_params, client_params
                    )

                response.status_headers.replace_header("Location", location)

        return response

    def modify_tag_attrs(self, tag, attrs):
        """Modify tag attributes or let `pywb` default behavior take over.

        :param tag: Tag being rewritten
        :param attrs: List of tuples of key, value attributes
        :return: Tuple of (attrs, stop) where stop disables default `pywb`
            rewriting
        """
        stop = False

        # Replace any referrerpolicy attr values with "no-referrer-when-downgrade".
        #
        # This is to prevent sites from telling browsers not to send the
        # Referer header. We need the Referer header because we use it to
        # authenticate requests (see authentication.py).
        rewrites = {"referrerpolicy": lambda value: "no-referrer-when-downgrade"}

        # Disable pywb's from rewriting the href URLs of <a> tags.
        #
        # We don't want users to stay within Via when clicking on a link,
        # we want clicking a link to take users to the target site directly
        # (not proxied by Via).
        if tag == "a":
            rewrites["href"] = lambda value: self.context.make_absolute(
                value, proxy=False
            )
            stop = True

        attrs = [
            (key, rewrites[key](value) if key in rewrites else value)
            for key, value in attrs
        ]

        return attrs, stop

    @classmethod
    def get_upstream_url(cls, doc_url):
        """Modify the URL before we attempt to get it from ourselves."""

        # The major reason to do this is to ensure the "canonical" URL in the
        # page is correct. Most other URLs are resources in the page which
        # don't have any of our params anyway
        return Configuration.strip_from_url(doc_url)
