from unittest.mock import create_autospec, patch

import pytest
from h_matchers import Any
from pytest import param
from pywb.apps.rewriterapp import RewriterApp

from viahtml.app import Application


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

    def test_it_wraps_pywb(self, app, start_response):
        result = app({}, start_response)

        assert result == start_response.return_value

        start_response.assert_called_with(self.STATUS, Any())

    def test_it_modifies_inbound_headers(self, app, start_response, environ):
        app(environ, start_response)

        modify_inbound = app.hooks.headers.modify_inbound
        modify_inbound.assert_called_once_with(environ)
        app.app.assert_called_once_with(modify_inbound.return_value, Any.function())

    def test_it_modifies_outbound_headers(self, app, start_response, environ, headers):
        result = app(environ, start_response)

        assert result == start_response.return_value
        modified_outbound = app.hooks.headers.modify_outbound
        modified_outbound.assert_called_once_with(headers)
        start_response.assert_called_with(Any(), modified_outbound.return_value)

    def test_it_adds_context_headers(self, app, start_response, environ, Context):
        Context.return_value.headers = [("X-Foo", "Foo")]

        app(environ, start_response)

        modified_outbound = app.hooks.headers.modify_outbound
        modified_outbound.assert_called_once_with(
            [
                # From the fixtures
                ("Header", "Value"),
                ("X-Foo", "Foo"),
            ]
        )

    @pytest.mark.parametrize("return_value", (["Hello"], []))
    # pylint: disable=too-many-arguments
    def test_it_applies_views(
        self, view, app, start_response, environ, return_value, Context
    ):
        view.return_value = return_value

        result = app(environ, start_response)

        Context.assert_called_once_with(environ, start_response)
        view.assert_called_once_with(Context.return_value)
        assert result == view.return_value

    def test_it_does_not_apply_views_if_they_have_no_return_value(
        self, view, app, start_response, environ
    ):
        view.return_value = None

        result = app(environ, start_response)

        assert result == start_response.return_value

    @pytest.fixture
    def view(self, app):
        view = create_autospec(
            lambda context: None, spec_set=True, return_value=None
        )  # pragma: no cover
        app.views = [view]

        return view

    @pytest.fixture
    def environ(self):
        # Worst fixture ever, but we don't really rely on the contents of the
        # WSGI environ for these tests. But it needs to have a 'get' method
        return {"environ": 1}

    @pytest.fixture
    def app(self):
        return Application()

    @pytest.fixture
    def headers(self):
        return [("Header", "Value")]

    @pytest.fixture(autouse=True)
    def FrontEndApp(self, patch, headers):
        FrontEndApp = patch("viahtml.app.FrontEndApp")

        # It's not in the spec, but this should have this object once
        # created. It needs to be present, but not anything in particular

        app = FrontEndApp.return_value
        app.rewriterapp = "something"

        # When the app is called, we need it to fake serving a request
        app.side_effect = lambda environ, start_request: start_request(
            self.STATUS, headers
        )

        return FrontEndApp

    @pytest.fixture(autouse=True)
    def apply_post_app_hooks(self, patch):
        return patch("viahtml.app.apply_post_app_hooks")

    @pytest.fixture(autouse=True)
    def Context(self, patch):
        Context = patch("viahtml.app.Context")
        Context.return_value.headers = []

        return Context


pytestmark = pytest.mark.usefixtures("os")


@pytest.fixture(autouse=True)
def Hooks():
    with patch("viahtml.app.Hooks", autospec=True) as Hooks:
        yield Hooks
