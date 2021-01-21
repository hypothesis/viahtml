"""The WSGI app."""
import logging
import os

from pkg_resources import resource_filename
from pywb.apps.frontendapp import FrontEndApp
from werkzeug.wsgi import get_path_info

from viahtml.hooks import Hooks
from viahtml.patch import apply_post_app_hooks, apply_pre_app_hooks
from viahtml.views.blocklist import BlocklistView
from viahtml.views.robots import RobotsView
from viahtml.views.routing import RoutingView
from viahtml.views.status import StatusView


class Application:
    """A collection of tools to create and configure `pywb`."""

    def __init__(self):
        self._set_config_file()

        config = self._config_from_env()
        self._setup_logging(config["debug"])
        self.hooks = Hooks(config)

        self.views = (
            StatusView(),
            BlocklistView(config["checkmate_host"]),
            RoutingView(config["routing_host"]),
            RobotsView(),
        )

        # Setup hook points and apply those which must be done pre-application
        apply_pre_app_hooks(self.hooks)

        self.app = FrontEndApp()

        # Setup hook points after the app is loaded
        apply_post_app_hooks(self.app.rewriterapp, self.hooks)

    def __call__(self, environ, start_response):
        """Handle WSGI requests."""

        for view in self.views:
            path = get_path_info(environ)
            response = view(path, environ, start_response)
            if response is not None:
                return response

        # Looks like it's a normal request to proxy...
        def proxy_start_response(status, headers):
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
            "ignore_prefixes": cls._split_multiline(os.environ["VIA_IGNORE_PREFIXES"]),
            "h_embed_url": os.environ["VIA_H_EMBED_URL"],
            "debug": os.environ.get("VIA_DEBUG", False),
            "routing_host": os.environ["VIA_ROUTING_HOST"],
            "checkmate_host": os.environ["CHECKMATE_URL"],
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
