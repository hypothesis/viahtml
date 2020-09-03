"""The WSGI app."""

import logging
import os

from pkg_resources import resource_filename
from pywb.apps.frontendapp import FrontEndApp

# I've no idea how we aren't hitting coverage on these lines
from viahtml.hooks import Hooks  # pragma: no cover
from viahtml.patch import apply_post_app_hooks, apply_pre_app_hooks  # pragma: no cover


class Application:
    """A collection of tools to create and configure `pywb`."""

    @classmethod
    def create(cls):
        """Create a WSGI application for proxying HTML."""

        # Move into the correct directory as template paths are relative
        os.chdir(resource_filename("viahtml", "."))
        config_file = os.environ["PYWB_CONFIG_FILE"] = "pywb_config.yaml"

        if not os.path.exists(config_file):
            config_file = os.path.abspath(config_file)
            raise EnvironmentError(f"Cannot find expected config {config_file}")

        config = cls._config_from_env()
        cls._setup_logging(config["debug"])

        # Setup hook points and apply those which must be done pre-application
        hooks = Hooks(config)
        apply_pre_app_hooks(hooks)

        app = FrontEndApp()

        # Setup hook points after the app is loaded
        apply_post_app_hooks(app.rewriterapp, hooks)

        return app

    @classmethod
    def _setup_logging(cls, debug=False):
        if debug:
            print("Enabling debug level logging")

        logging.basicConfig(
            format="%(asctime)s: [%(levelname)s]: %(message)s",
            level=logging.DEBUG if debug else logging.INFO,
        )

    @classmethod
    def _config_from_env(cls):
        """Parse options from environment variables."""

        return {
            "ignore_prefixes": cls._split_multiline(os.environ["VIA_IGNORE_PREFIXES"]),
            "h_embed_url": os.environ["VIA_H_EMBED_URL"],
            "debug": os.environ.get("VIA_DEBUG", False),
        }

    @classmethod
    def _split_multiline(cls, value):
        return [part for part in [p.strip() for p in value.split(",")] if part]
