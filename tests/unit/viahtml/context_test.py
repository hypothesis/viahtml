from http import HTTPStatus

import pytest

from viahtml.context import Context


class TestContext:
    @pytest.mark.parametrize(
        "prop,wsgi_method",
        (
            ("path", "get_path_info"),
            ("url", "get_current_url"),
            ("host", "get_host"),
        ),
    )
    def test_pass_through_properties(
        self, context, environ, wsgi, prop, wsgi_method
    ):  # pylint: disable=too-many-arguments
        value = getattr(context, prop)

        assert value == getattr(wsgi, wsgi_method).return_value
        getattr(wsgi, wsgi_method).assert_called_once_with(environ)

    @pytest.mark.parametrize(
        "path,proxied_url",
        (
            ("/", None),
            ("/http://example.com", "http://example.com"),
            ("/proxy/http://example.com", "http://example.com"),
            ("/proxy/oe_/http://example.com", "http://example.com"),
        ),
    )
    @pytest.mark.parametrize("query_string", ("", "via.config=1"))
    def test_proxied_url_with_config(
        self, context, environ, path, proxied_url, query_string
    ):  # pylint: disable=too-many-arguments
        # Not patching the wsgi functions here, as we aren't a straight map
        # We don't want to encode our misunderstanding of how they work
        environ["PATH_INFO"] = path
        environ["QUERY_STRING"] = query_string

        url = context.proxied_url_with_config

        if proxied_url is None:
            assert url is None
        else:
            assert url == proxied_url + (f"?{query_string}" if query_string else "")

    @pytest.mark.parametrize(
        "path,proxied_url",
        (
            ("/", None),
            ("/http://example.com", "http://example.com"),
        ),
    )
    @pytest.mark.parametrize("query_string", ("", "via.config=1"))
    def test_proxied_url(
        self, context, environ, path, proxied_url, query_string
    ):  # pylint: disable=too-many-arguments
        # Not patching the wsgi functions here, as we aren't a straight map
        # We don't want to encode our misunderstanding of how they work
        environ["PATH_INFO"] = path
        environ["QUERY_STRING"] = query_string

        url = context.proxied_url

        assert url == proxied_url

    def test_make_response(self, context, start_response):
        context.headers = [("X-Boo", "Boo")]

        response = context.make_response(
            HTTPStatus.BAD_REQUEST,
            headers={"X-Foo": "Foo"},
            lines=["Some text", "Some more"],
        )

        start_response.assert_called_once_with(
            "400 Bad Request", [("X-Boo", "Boo"), ("X-Foo", "Foo")]
        )
        assert response == [b"Some text", b"Some more"]

    def test_make_response_degenerate_call(self, context, start_response):
        response = context.make_response()

        start_response.assert_called_once_with("200 OK", [])
        assert response == []

    def test_make_json_response(self, context, start_response):
        context.headers = [("X-Boo", "Boo")]

        payload = {"json": "data"}

        response = context.make_json_response(
            payload,
            HTTPStatus.BAD_REQUEST,
            headers={"X-Foo": "Foo"},
        )

        start_response.assert_called_once_with(
            "400 Bad Request",
            [
                ("X-Boo", "Boo"),
                ("X-Foo", "Foo"),
                ("Content-Type", "application/json; charset=utf-8"),
            ],
        )
        assert response == [b'{"json": "data"}']

    def test_make_json_degenerate_call(self, context, start_response):
        context.make_json_response({})

        start_response.assert_called_once_with(
            "200 OK", [("Content-Type", "application/json; charset=utf-8")]
        )

    def test_add_header(self, context):
        context.add_header("X-Foo", "Foo")

        assert context.headers == [("X-Foo", "Foo")]

    def test_get_header_reads_from_environ(self, context, environ):
        environ["HTTP_X_FOO"] = "Foo!"

        value = context.get_header("X-Foo")

        assert value == "Foo!"

    @pytest.mark.parametrize("header_name", ("X-Foo", "x-Foo", "X-foo", "x-foo"))
    def test_get_header_reads_added_headers(self, context, environ, header_name):
        # Noise must come first to get coverage
        context.add_header("X-Noise", "Noo")
        context.add_header(header_name, "Foo!")
        environ["HTTP_X_FOO"] = "Noo"

        value = context.get_header("X-Foo")

        assert value == "Foo!"

    @pytest.mark.parametrize(
        "url,proxy,expected",
        (
            ("/proxy/http://example.com", True, "http://via/proxy/http://example.com"),
            (
                "//via/proxy/http://example.com",
                True,
                "http://via/proxy/http://example.com",
            ),
            (
                "http://via/proxy/http://example.com",
                True,
                "http://via/proxy/http://example.com",
            ),
            ("subpath", False, "https://example.com/path/subpath"),
            ("/path2", False, "https://example.com/path2"),
            ("//example.com", False, "https://example.com"),
            ("ftp://example.com", False, "ftp://example.com"),
        ),
    )
    def test_make_absolute(
        self, context, url, proxy, expected, environ
    ):  # pylint: disable=too-many-arguments
        environ["PATH_INFO"] = "/proxy/https://example.com/path/"

        result = context.make_absolute(url, proxy)

        assert result == expected

    @pytest.fixture
    def environ(self):
        return {
            "wsgi.url_scheme": "http",
            "SERVER_NAME": "via",
            "SERVER_PORT": "9999",
            "SCRIPT_NAME": "script",
            "PATH_INFO": "/",
        }

    @pytest.fixture
    def context(self, environ, start_response):
        return Context(environ, start_response)

    @pytest.fixture
    def wsgi(self, patch):
        return patch("viahtml.context.wsgi")
