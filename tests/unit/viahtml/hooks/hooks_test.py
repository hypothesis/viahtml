from unittest.mock import patch, sentinel

import pytest
from h_matchers import Any
from pywb.apps.wbrequestresponse import WbResponse
from warcio.statusandheaders import StatusAndHeaders

from viahtml.hooks import Hooks


class TestHooks:
    def test_template_vars(self, hooks):
        assert hooks.template_vars == {
            "client_params": Any.function(),
            "external_link_mode": Any.function(),
            # Just persisting the configuration
            "ignore_prefixes": hooks.ignore_prefixes,
            "http_mode": False,
        }

    def test_client_params_in_template_vars(self, hooks):
        with patch.object(hooks, "get_config") as get_config:
            get_config.return_value = ["via", "client"]
            client_params = hooks.template_vars["client_params"]

            params = client_params(sentinel.http_env)

            assert params == "client"
            get_config.assert_called_once_with(sentinel.http_env)

    @pytest.mark.parametrize(
        "link_mode,expected",
        (
            ("new-tab", "new-tab"),
            ("same-tab", "same-tab"),
            (None, "same-tab"),
            ("random", "random"),
        ),
    )
    def test_external_link_mode_in_template_vars(self, hooks, link_mode, expected):
        http_env = {}
        if link_mode is not None:
            http_env["QUERY_STRING"] = f"via.external_link_mode={link_mode}"

        external_link_mode = hooks.template_vars["external_link_mode"]

        assert external_link_mode(http_env) == expected

    def test_ignore_prefixes(self, hooks):
        assert hooks.ignore_prefixes == sentinel.prefixes

    def test_get_config(self, Configuration, hooks):
        config = hooks.get_config(sentinel.http_env)

        Configuration.extract_from_wsgi_environment.assert_called_once_with(
            sentinel.http_env
        )
        assert config == Configuration.extract_from_wsgi_environment.return_value

    def test_get_upstream_url(self, hooks, Configuration):
        config = hooks.get_upstream_url(sentinel.doc_url)

        Configuration.strip_from_url.assert_called_once_with(sentinel.doc_url)
        assert config == Configuration.strip_from_url.return_value

    @pytest.mark.parametrize(
        "status_line",
        (
            "301 Moved Permanently",
            "302 Found",
            "303 See Other",
            "305 Use Proxy",
            "307 Temporary Redirect",
            "308 Permanent Redirect",
        ),
    )
    def test_modify_render_response_rewrites_redirects(
        self, hooks, wb_response, status_line
    ):
        wb_response.status_headers.statusline = status_line
        wb_response.status_headers.add_header("Location", "foo")

        response = hooks.modify_render_response(wb_response, {})

        location = response.status_headers.get_header("Location")
        assert location == Any.url.with_query({"via.sec": Any.string()})

    def test_modify_render_response_survives_no_location(self, hooks, wb_response):
        wb_response.status_headers.statusline = "307 Temporary Redirect"

        response = hooks.modify_render_response(wb_response, {})

        assert response == wb_response

    @pytest.mark.parametrize(
        "status_line",
        (
            "304 Not Modified",
            "200 Ok",
        ),
    )
    def test_modify_render_response_does_not_modify_other_requests(
        self, hooks, status_line, wb_response
    ):
        wb_response.status_headers.statusline = status_line
        wb_response.status_headers.add_header("Location", "foo")

        response = hooks.modify_render_response(wb_response, {})

        location = response.status_headers.get_header("Location")
        assert location == "foo"

    @pytest.mark.parametrize(
        "location",
        (
            "https://via/proxy/http://example.com",
            "//via/proxy/http://example.com",
            "/proxy/http://example.com",
        ),
    )
    def test_modify_render_response_makes_locations_absolute(
        self, hooks, wb_response, location
    ):
        wb_response.status_headers.statusline = "307 Temporary Redirect"
        wb_response.status_headers.add_header("Location", location)

        response = hooks.modify_render_response(wb_response, {})

        location = response.status_headers.get_header("Location")
        assert (
            location
            == Any.url.matching(f"https://via/proxy/http://example.com").with_query()
        )

    @pytest.mark.parametrize("http_mode", (True, False))
    def test_modify_render_response_reads_the_http_mode(
        self, hooks, wb_response, http_mode
    ):
        hooks.config["http_mode"] = True
        wb_response.status_headers.statusline = "307 Temporary Redirect"
        wb_response.status_headers.add_header("Location", "//proxy/http://example.com")

        response = hooks.modify_render_response(wb_response, {})

        location = response.status_headers.get_header("Location")
        assert location == Any.url.with_scheme("http")

    @pytest.fixture
    def wb_response(self):
        return WbResponse(status_headers=StatusAndHeaders("200 OK", headers=[]))

    @pytest.fixture
    def hooks(self):
        return Hooks(
            {
                "ignore_prefixes": sentinel.prefixes,
                "secret": "not_a_secret",
                "http_mode": False,
            }
        )

    @pytest.fixture
    def Configuration(self):
        with patch("viahtml.hooks.hooks.Configuration", autospec=True) as Configuration:
            yield Configuration

    @pytest.fixture(autouse=True)
    def Context(self, patch):
        Context = patch("viahtml.hooks.hooks.Context")
        Context.return_value.host = "via"
        return Context
