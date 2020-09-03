import os
from unittest.mock import patch

import pytest
from h_matchers import Any
from pytest import param
from pywb.apps.frontendapp import FrontEndApp
from pywb.apps.rewriterapp import RewriterApp

from viahtml.app import Application


# For reasons I find absolutely mysterious, everytime we create our app
# coverage can no longer be detected on lines following it. We absolutely get
# there but for some reason it doesn't show in the report?
class TestApplicationCreate:  # pragma: no cover
    def test_it_returns_an_app(self):
        app = Application.create()

        assert isinstance(app, FrontEndApp)

    @patch("viahtml.app.apply_pre_app_hooks", autospec=True)
    def test_it_applies_pre_app_hooks(self, apply_pre_app_hooks, Hooks):
        Application.create()

        apply_pre_app_hooks.assert_called_once_with(Hooks.return_value)

    @patch("viahtml.app.apply_post_app_hooks", autospec=True)
    def test_it_applies_post_app_hooks(self, apply_post_app_hooks, Hooks):
        Application.create()

        apply_post_app_hooks.assert_called_once_with(
            Any.instance_of(RewriterApp), Hooks.return_value
        )

    @pytest.mark.parametrize(
        "variable,value,expected",
        (
            ("VIA_DEBUG", "value", {"debug": "value"}),
            (
                "VIA_IGNORE_PREFIXES",
                "  value_1, value_2 ",
                {"ignore_prefixes": ["value_1", "value_2"]},
            ),
            ("VIA_H_EMBED_URL", "value", {"h_embed_url": "value"}),
        ),
    )
    def test_it_reads_options_from_environment_variables(
        self, variable, value, expected, Hooks
    ):
        os.environ[variable] = value

        Application.create()

        Hooks.assert_called_once_with(Any.dict.containing(expected))

    def test_it_sets_the_config_file_for_pywb(self):
        Application.create()

        assert os.environ["PYWB_CONFIG_FILE"] == "pywb_config.yaml"

    @patch("os.path.exists", autospec=True)
    def test_it_detects_missing_config_file(self, exists):
        exists.return_value = False

        with pytest.raises(EnvironmentError):
            Application.create()

    @pytest.mark.parametrize(
        "debug_enabled",
        (
            param("1", id="debug"),
            param("", id="no debug"),
        ),
    )
    def test_it_configures_logging(self, debug_enabled):
        os.environ["VIA_DEBUG"] = debug_enabled

        with patch("viahtml.app.logging", autospec=True) as logging:
            Application.create()

            logging.basicConfig.assert_called_once_with(
                format=Any.string(),
                level=logging.DEBUG if debug_enabled else logging.INFO,
            )

    @pytest.fixture
    def Hooks(self):
        with patch("viahtml.app.Hooks", autospec=True) as Hooks:
            yield Hooks
