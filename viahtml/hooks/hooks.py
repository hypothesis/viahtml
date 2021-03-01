"""The majority of configuration options."""
from h_vialib import Configuration
from h_vialib.secure import ViaSecureURL

from viahtml.hooks._headers import Headers


class Hooks:
    """A collection of configuration points for `pywb`."""

    headers = Headers()

    def __init__(self, config):
        self.config = config
        self._secure_url = ViaSecureURL(config["secret"])
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
            # This is a redirect, so we'll sign it to ensure we know it
            # came from us. This prevents long redirect chains from breaking
            # our referrer checking
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

                location = self._secure_url.create(location)
                response.status_headers.replace_header("Location", location)

        return response

    def modify_tag_attrs(self, tag, attrs):
        """Modify tag attributes or let `pywb` default behavior take over.

        :param tag: Tag being rewritten
        :param attrs: List of tuples of key, value attributes
        :return: None for default behavior, or attrs to write in the same
            format as received
        """
        # Prevent any rewriting of tags if we are configured to
        if tag == "a" and not self.config["rewrite"]["a_href"]:

            def value_map(key, value):
                if key == "href":
                    value = self.context.make_absolute(value, proxy=False)

                return key, value

            return [value_map(key, value) for key, value in attrs]

        # Allow everything else through
        return None

    @classmethod
    def get_upstream_url(cls, doc_url):
        """Modify the URL before we attempt to get it from ourselves."""

        # The major reason to do this is to ensure the "canonical" URL in the
        # page is correct. Most other URLs are resources in the page which
        # don't have any of our params anyway
        return Configuration.strip_from_url(doc_url)
