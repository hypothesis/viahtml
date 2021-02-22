from unittest.mock import create_autospec, patch, sentinel

import pytest
from h_matchers import Any
from pywb.apps.wbrequestresponse import WbResponse
from warcio.statusandheaders import StatusAndHeaders

from viahtml.context import Context
from viahtml.hooks import Hooks


class TestHooks:
    def test_template_vars(self, hooks):
        assert hooks.template_vars == {
            "client_params": Any.function(),
            "external_link_mode": Any.function(),
            "h_embed_url": sentinel.h_embed_url,
            "ignore_prefixes": hooks.ignore_prefixes,
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
        original_location = "http://via/proxy/http://example.com"
        wb_response.status_headers.add_header("Location", original_location)

        response = hooks.modify_render_response(wb_response)

        location = response.status_headers.get_header("Location")
        hooks.context.make_absolute.assert_called_once_with(original_location)
        assert location == Any.url.matching(original_location).containing_query(
            {"via.sec": Any.string()}
        )

    def test_modify_render_response_preserves_via_params_on_redirect(
        self, hooks, wb_response, context
    ):
        context.http_environ = {"QUERY_STRING": "via.option=foo"}
        wb_response.status_headers.statusline = "307 Temporary Redirect"
        wb_response.status_headers.add_header("Location", "http://example.com")

        response = hooks.modify_render_response(wb_response)

        location = response.status_headers.get_header("Location")

        assert location == Any.url.containing_query({"via.option": "foo"})

    def test_modify_render_response_survives_no_location(self, hooks, wb_response):
        wb_response.status_headers.statusline = "307 Temporary Redirect"

        response = hooks.modify_render_response(wb_response)

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

        response = hooks.modify_render_response(wb_response)

        location = response.status_headers.get_header("Location")
        assert location == "foo"

    @pytest.mark.parametrize(
        "tag,attrs,rewrite_settings,expected",
        (
            # When rewriting is _disabled_ and we have an <a> tag we return
            # something to prevent pywb from rewriting the <a> tag's `src`.
            (
                "a",
                [("href", "foo"), ("a", "b")],
                {"a_href": False},
                [("href", "ABS:foo"), ("a", "b")],
            ),
            # In all other cases we return None to allow pywb's behavior.
            ("h1", [], {"a_href": False}, None),
            ("a", [("href", "foo")], {"a_href": True}, None),
            ("h1", [], {"a_href": True}, None),
        ),
    )
    def test_modify_tag_attrs_disables_rewriting(
        self, hooks, tag, attrs, rewrite_settings, expected
    ):  # pylint: disable=too-many-arguments
        hooks.config["rewrite"] = rewrite_settings
        hooks.context.make_absolute.side_effect = lambda url, proxy=True: "ABS:" + url

        new_attrs = hooks.modify_tag_attrs(tag, attrs)
        assert new_attrs == expected

    @pytest.fixture
    def wb_response(self):
        return WbResponse(status_headers=StatusAndHeaders("200 OK", headers=[]))

    @pytest.fixture
    def context(self):
        context = create_autospec(Context, spec_set=True, instance=True)
        context.host = "via"
        context.make_absolute.side_effect = lambda url, proxy=True: url
        return context

    @pytest.fixture
    def hooks(self, context):
        hooks = Hooks(
            {
                "config_noise": "noise",
                "h_embed_url": sentinel.h_embed_url,
                "ignore_prefixes": sentinel.prefixes,
                "secret": "not_a_secret",
                "rewrite": {"a_href": True},
            }
        )

        hooks.set_context(context)

        return hooks

    @pytest.fixture
    def Configuration(self):
        with patch("viahtml.hooks.hooks.Configuration", autospec=True) as Configuration:
            yield Configuration
