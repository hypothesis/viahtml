import pytest
from h_matchers import Any
from pytest import param

from viahtml.hooks._headers import Headers


class TestHeaders:
    def test_environ_name(self):
        assert Headers.environ_name("mIxed-Case") == "HTTP_MIXED_CASE"

    @pytest.mark.parametrize("header_name", Headers.BLOCKED_INBOUND)
    def test_modify_inbound_removes_blocked_items(self, headers, header_name):
        http_env = {
            "HTTP_OTHER_HEADER": "ok",
            Headers.environ_name(header_name): "blocked",
        }

        http_env = headers.modify_inbound(http_env)

        assert Headers.environ_name(header_name) not in http_env
        assert "HTTP_OTHER_HEADER" in http_env

    @pytest.mark.parametrize(
        "header_name", Headers.BLOCKED_OUTBOUND | {"X-Archive-Anything-At-All"}
    )
    def test_modify_outbound_removes_blocked_items(
        self, headers, header_name, string_case
    ):
        # A header that modify_outbound() should remove.
        blocked_header = (string_case(header_name), "blocked")
        # A header that modify_outbound() should allow.
        expected_header = ("Other-Header", "ok")

        original_headers = [blocked_header, expected_header]

        modified_headers = headers.modify_outbound(original_headers)

        assert blocked_header not in modified_headers
        assert expected_header in modified_headers

    @pytest.mark.parametrize(
        "value,expected",
        (
            # Things we don't mess with
            ("invalid_header", "invalid_header"),
            ("no-cache, must-revalidate", "no-cache, must-revalidate"),
            ("max-age=604800", "max-age=604800"),
            ("private, max-age=0", "private, max-age=0"),
            ("private, max-age=604800", "private, max-age=604800"),
            # When the cache is public, and below cloudflare caching numbers, we
            # mark it as private only. The order changes a bit here too
            ("public, max-age=0", "max-age=0, private"),
            ("public, max-age=100", "max-age=100, private"),
            # Back to over the Cloudflare minimum
            ("public, max-age=604800", "public, max-age=604800"),
            # Ignore trailing non-digit chars in the max-age value, because this
            # is what browsers do.
            ("public, max-age=604800; ignore-me", "public, max-age=604800"),
            ("public, max-age=5000.23", "public, max-age=5000"),
            ("public, max-age=10.23", "max-age=10, private"),
            # Unparseable max-age values, treated as 0 to prevent Cloudflare
            # from caching for a minimum of 30 minutes.
            ("public, max-age=abc", "max-age=0, private"),
            ("public, max-age=", "max-age=0, private"),
        ),
    )
    def test_modify_outbound_translates_cache_control_headers(
        self, headers, value, expected, string_case
    ):
        modified_headers = headers.modify_outbound(
            ((string_case("X-Archive-Orig-Cache-Control"), value),)
        )

        cache_control_headers = [
            header
            for header in modified_headers
            if header[0].lower() == "cache-control"
        ]
        assert cache_control_headers == [("Cache-Control", expected)]

    def test_modify_outbound_inserts_noindex_header(self, headers):
        modified_headers = headers.modify_outbound([])

        assert modified_headers == Any.list.containing(
            [("X-Robots-Tag", "noindex, nofollow")]
        )

    @pytest.fixture(
        params=(
            param(lambda v: v, id="mixed case"),
            param(lambda v: v.lower(), id="lower case"),
            param(lambda v: v.upper(), id="upper case"),
        )
    )
    def string_case(self, request):
        return request.param

    @pytest.fixture
    def headers(self):
        return Headers()
