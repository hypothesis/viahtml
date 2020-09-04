# pylint: disable=wrong-import-order
from viahtml.app import Application  # isort:skip
from unittest.mock import patch

import pytest
from h_matchers import Any
from pytest import param
from pywb.apps.rewriterapp import RewriterApp


class TestApplicationCreate:
    @patch("viahtml.app.apply_pre_app_hooks", autospec=True)
    def test_it_applies_pre_app_hooks(self, apply_pre_app_hooks, Hooks):
        Application()

        apply_pre_app_hooks.assert_called_once_with(Hooks.return_value)

    @patch("viahtml.app.apply_post_app_hooks", autospec=True)
    def test_it_applies_post_app_hooks(self, apply_post_app_hooks, Hooks):
        Application()

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
    # pylint: disable=too-many-arguments
    def test_it_reads_options_from_environment_variables(
        self, variable, value, expected, Hooks, os
    ):
        os.environ[variable] = value

        Application()

        Hooks.assert_called_once_with(Any.dict.containing(expected))

    def test_it_sets_the_config_file_for_pywb(self, os):
        Application()

        assert os.environ["PYWB_CONFIG_FILE"] == "pywb_config.yaml"

    def test_it_detects_missing_config_file(self, os):
        os.path.exists.return_value = False

        with pytest.raises(EnvironmentError):
            Application()

    @pytest.mark.parametrize(
        "debug_enabled",
        (
            param("1", id="debug"),
            param("", id="no debug"),
        ),
    )
    def test_it_configures_logging(self, debug_enabled, os, logging):
        os.environ["VIA_DEBUG"] = debug_enabled

        Application()

        logging.basicConfig.assert_called_once_with(
            format=Any.string(),
            level=logging.DEBUG if debug_enabled else logging.INFO,
        )

    @pytest.fixture
    def logging(self):
        with patch("viahtml.app.logging", autospec=True) as logging:
            yield logging

    @pytest.fixture
    def Hooks(self):
        with patch("viahtml.app.Hooks", autospec=True) as Hooks:
            yield Hooks
