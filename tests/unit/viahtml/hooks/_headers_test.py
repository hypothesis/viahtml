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

    def test_modify_inbound_inserts_abuse_headers(self, headers):
        http_env = {"HTTP_OTHER_HEADER": "ok"}

        http_env = headers.modify_inbound(http_env)

        assert http_env == {
            "HTTP_OTHER_HEADER": "ok",
            "HTTP_X_ABUSE_POLICY": "https://web.hypothes.is/abuse-policy/",
            "HTTP_X_COMPLAINTS_TO": "https://web.hypothes.is/report-abuse/",
        }

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
        "header,value",
        (
            ("Cross-Origin-Opener-Policy", "same-origin"),
            ("Cross-Origin-Embedder-Policy", "require-corp"),
        ),
    )
    def test_modify_outbound_removes_the_cross_origin_policies(
        self, headers, string_case, header, value
    ):
        # The test above only covers the headers that are in BLOCKED_OUTBOUND,
        # so it would still pass if one of these was taken out of the list.
        # This test names the headers so that it would fail instead.
        original_headers = [
            (string_case(header), value),
            ("Other-Header", "ok"),
        ]

        modified_headers = headers.modify_outbound(original_headers)

        header_names = [name.lower() for name, _value in modified_headers]
        assert header.lower() not in header_names
        assert "other-header" in header_names

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
