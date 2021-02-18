"""The majority of configuration options."""
from h_vialib import Configuration
from h_vialib.secure import ViaSecureURL

from viahtml.context import Context
from viahtml.hooks._headers import Headers


class Hooks:
    """A collection of configuration points for `pywb`."""

    headers = Headers()

    def __init__(self, config):
        self.config = config
        self._secure_url = ViaSecureURL(config["secret"])

    @property
    def template_vars(self):
        """Get variables to make available in the global Jinja2 environment."""

        def external_link_mode(http_env):
            via_config, _ = self.get_config(http_env)
            return via_config.get("external_link_mode", "same-tab").lower()

        template_vars = {
            # It would be much nicer to calculate this once somehow
            "client_params": lambda http_env: self.get_config(http_env)[1],
            "external_link_mode": external_link_mode,
        }

        template_vars.update(self.config)
        template_vars.pop("secret")

        # This is already in the config, but run through the property just in
        # case that grows some logic in it
        template_vars["ignore_prefixes"] = self.ignore_prefixes

        return template_vars

    @property
    def ignore_prefixes(self):
        """Get the list of URL prefixes to ignore (server and client side)."""

        return self.config["ignore_prefixes"]

    @classmethod
    def get_config(cls, http_env):
        """Return the h-client parameters from a WSGI environment."""

        return Configuration.extract_from_wsgi_environment(http_env)

    _REDIRECTS = ("301", "302", "303", "305", "307", "308")

    def modify_render_response(self, response, environ):
        """Return a potentially modified response from pywb.

        :param response: WbResponse object returned from pywb
        :param environ: WSGI environ dict
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
                location = Context(environ, start_response=None).make_absolute(location)
                location = self._secure_url.create(location)
                response.status_headers.replace_header("Location", location)

        return response

    @classmethod
    def get_upstream_url(cls, doc_url):
        """Modify the URL before we attempt to get it from ourselves."""

        # The major reason to do this is to ensure the "canonical" URL in the
        # page is correct. Most other URLs are resources in the page which
        # don't have any of our params anyway
        return Configuration.strip_from_url(doc_url)
