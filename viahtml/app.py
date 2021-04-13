"""The WSGI app."""
import logging
import os

# isort: off
# This import has to come before the CheckmateClient import or the functional
# tests break.
# See https://github.com/gevent/gevent/issues/1016
from pywb.apps.frontendapp import FrontEndApp

# isort: on

from checkmatelib import CheckmateClient
from pkg_resources import resource_filename

from viahtml.context import Context
from viahtml.hooks import Hooks
from viahtml.patch import apply_post_app_hooks, apply_pre_app_hooks
from viahtml.views.authentication import AuthenticationView
from viahtml.views.blocklist import BlocklistView
from viahtml.views.routing import RoutingView
from viahtml.views.status import StatusView


def asbool(value):
    """Return True if value is any of "t", "true", "y", etc (case-insensitive)."""
    return str(value).strip().lower() in ("t", "true", "y", "yes", "on", "1")


class Application:
    """A collection of tools to create and configure `pywb`."""

    def __init__(self):
        self._set_config_file()

        config = self._config_from_env()

        self._config = config
        self._setup_logging(config["debug"])
        self.hooks = Hooks(config)

        checkmate = CheckmateClient(
            config["checkmate_host"], config["checkmate_api_key"]
        )

        self.views = (
            StatusView(checkmate),
            AuthenticationView(
                required=not config["disable_authentication"],
                allowed_referrers=config["allowed_referrers"],
            ),
            BlocklistView(
                checkmate,
                asbool(config.get("checkmate_allow_all")),
                config["checkmate_ignore_reasons"],
            ),
            RoutingView(config["routing_host"]),
        )

        # Setup hook points and apply those which must be done pre-application
        apply_pre_app_hooks(self.hooks)

        self.app = FrontEndApp()

        # Setup hook points after the app is loaded
        apply_post_app_hooks(self.app.rewriterapp, self.hooks)

    def __call__(self, environ, start_response):
        """Handle WSGI requests."""

        context = Context(http_environ=environ, start_response=start_response)
        self.hooks.set_context(context)

        for view in self.views:
            response = view(context)
            if response is not None:
                return response

        # Looks like it's a normal request to proxy...
        def proxy_start_response(status, headers):
            # If any of our views added headers as they went, add them now
            if context.headers:
                headers.extend(context.headers)

            headers = self.hooks.headers.modify_outbound(headers)

            return start_response(status, headers)

        environ = self.hooks.headers.modify_inbound(environ)
        return self.app(environ, proxy_start_response)

    @classmethod
    def _set_config_file(cls):
        # Move into the correct directory as template paths are relative
        os.chdir(resource_filename("viahtml", "."))
        config_file = os.environ["PYWB_CONFIG_FILE"] = "pywb_config.yaml"

        if not os.path.exists(config_file):
            config_file = os.path.abspath(config_file)
            raise EnvironmentError(f"Cannot find expected config {config_file}")

    @classmethod
    def _config_from_env(cls):
        """Parse options from environment variables."""

        return {
            "allowed_referrers": cls._split_multiline(
                os.environ.get("VIA_ALLOWED_REFERRERS", "")
            ),
            "ignore_prefixes": cls._split_multiline(os.environ["VIA_IGNORE_PREFIXES"]),
            "h_embed_url": os.environ["VIA_H_EMBED_URL"],
            "debug": os.environ.get("VIA_DEBUG", False),
            "routing_host": os.environ["VIA_ROUTING_HOST"],
            "disable_authentication": asbool(
                os.environ.get("VIA_DISABLE_AUTHENTICATION", False)
            ),
            "checkmate_host": os.environ["CHECKMATE_URL"],
            "checkmate_ignore_reasons": os.environ.get("CHECKMATE_IGNORE_REASONS"),
            "checkmate_api_key": os.environ["CHECKMATE_API_KEY"],
            "checkmate_allow_all": os.environ.get("CHECKMATE_ALLOW_ALL"),
        }

    @classmethod
    def _setup_logging(cls, debug=False):
        if debug:
            print("Enabling debug level logging")

        logging.basicConfig(
            format="%(asctime)s: [%(levelname)s]: %(message)s",
            level=logging.DEBUG if debug else logging.INFO,
        )

    @classmethod
    def _split_multiline(cls, value):
        return [part for part in [p.strip() for p in value.split(",")] if part]
