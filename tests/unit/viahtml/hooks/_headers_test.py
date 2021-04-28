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

    def test_cache_control_header_is_set_to_no_store(self, headers):
        modified_headers = headers.modify_outbound(tuple())

        assert modified_headers == Any.list.containing([("Cache-Control", "no-store")])

    def test_modify_outbound_inserts_referrer_policy_header(self, headers):
        modified_headers = headers.modify_outbound([])

        assert modified_headers == Any.list.containing(
            [("Referrer-Policy", "no-referrer-when-downgrade")]
        )

    def test_modify_outbound_inserts_noindex_header(self, headers):
        modified_headers = headers.modify_outbound([])

        assert modified_headers == Any.list.containing(
            [("X-Robots-Tag", "noindex, nofollow")]
        )

    def test_modify_outbound_inserts_abuse_headers(self, headers):
        modified_headers = headers.modify_outbound([])

        assert modified_headers == Any.list.containing(
            [
                ("X-Abuse-Policy", "https://web.hypothes.is/abuse-policy/"),
                ("X-Complaints-To", "https://web.hypothes.is/report-abuse/"),
            ]
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
