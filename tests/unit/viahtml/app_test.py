# pylint: disable=wrong-import-order
from viahtml.app import Application  # isort:skip

from unittest.mock import create_autospec, patch, sentinel

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


class TestApplication:
    # Test the WSGI middleware wrapping behavior
    # This is a small amount code which generates a huge and annoying amount of
    # test code as it's very nested and functional

    STATUS = "200 OK"
    HEADERS = (("Header", "Value"),)

    def test_it_wraps_pywb(self, app, start_response):
        print(app.hooks)
        result = app(sentinel.environ, start_response)

        assert result == start_response.return_value

        start_response.assert_called_with(self.STATUS, Any())

    def test_it_modifies_inbound_headers(self, app, start_response):
        app(sentinel.environ, start_response)

        modify_inbound = app.hooks.headers.modify_inbound
        modify_inbound.assert_called_once_with(sentinel.environ)
        app.app.assert_called_once_with(modify_inbound.return_value, Any.function())

    def test_it_modifies_outbound_headers(self, app, start_response):
        result = app(sentinel.environ, start_response)

        assert result == start_response.return_value
        modified_outbound = app.hooks.headers.modify_outbound
        modified_outbound.assert_called_once_with(self.HEADERS)
        start_response.assert_called_with(Any(), modified_outbound.return_value)

    @pytest.fixture
    def start_response(self):
        return create_autospec(lambda status, headers: None)  # pragma: no cover

    @pytest.fixture
    def app(self):
        return Application()

    @pytest.fixture(autouse=True)
    def FrontEndApp(self, patch):
        FrontEndApp = patch("viahtml.app.FrontEndApp")

        # It's not in the spec, but this should have this object once
        # created. It needs to be present, but not anything in particular

        app = FrontEndApp.return_value
        app.rewriterapp = "something"

        # When the app is called, we need it to fake serving a request
        app.side_effect = lambda environ, start_request: start_request(
            self.STATUS, self.HEADERS
        )

        return FrontEndApp

    @pytest.fixture(autouse=True)
    def apply_post_app_hooks(self, patch):
        return patch("viahtml.app.apply_post_app_hooks")


@pytest.fixture(autouse=True)
def Hooks():
    with patch("viahtml.app.Hooks", autospec=True) as Hooks:
        yield Hooks
