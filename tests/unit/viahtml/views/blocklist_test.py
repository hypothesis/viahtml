from unittest.mock import create_autospec, sentinel

import pytest
from h_matchers import Any

from viahtml.blocklist import Blocklist as Blocklist_
from viahtml.views.blocklist import BlocklistView


class TestBlocklistView:
    def test_construction(self, Blocklist):
        view = BlocklistView(sentinel.file_name)

        Blocklist.assert_called_once_with(sentinel.file_name)
        assert view.blocklist == Blocklist.return_value

    @pytest.mark.parametrize(
        "path,expected",
        (
            ("/proxy/http://example.com", "http://example.com"),
            ("/static/something.jpg", None),
        ),
    )
    def test_it_extracts_the_url_correctly(self, path, expected):
        proxied_url = BlocklistView.get_proxied_url(path)
        assert proxied_url == expected

    def test_if_there_is_no_url_it_does_nothing(self, view, start_response):
        result = view("", {}, start_response)

        assert result is None
        view.blocklist.assert_not_called()

    def test_if_the_url_is_not_blocked_it_does_nothing(self, view, start_response):
        view.blocklist.is_blocked.return_value = None

        result = view("/proxy/http://example.com", {}, start_response)

        assert result is None
        view.blocklist.is_blocked.assert_called_once_with("http://example.com")

    @pytest.mark.parametrize(
        "block_reason,expected_heading",
        (
            (Blocklist_.Reason.MALICIOUS, "Deceptive site ahead"),
            (Blocklist_.Reason.MEDIA_VIDEO, "Content cannot be annotated"),
            (Blocklist_.Reason.HIGH_IO, "Content cannot be annotated"),
            (Blocklist_.Reason.PUBLISHER_BLOCKED, "Content not available"),
        ),
    )
    def test_blocking(self, view, block_reason, start_response, expected_heading):
        view.blocklist.is_blocked.return_value = block_reason

        result = view("/proxy/http://example.com", {}, start_response)

        start_response.assert_called_once_with(
            "403 Forbidden", [("Content-Type", "text/html; charset=utf-8")]
        )

        assert result == Any.list.of_size(1)
        assert expected_heading in result[0].decode("utf-8")

    @pytest.fixture
    def start_response(self):
        def start_response(message, headers):  # pragma: no cover
            ...

        return create_autospec(start_response, spec_set=True)

    @pytest.fixture
    def view(self):
        return BlocklistView(sentinel.file_name)


@pytest.fixture(autouse=True)
def Blocklist(patch):
    return patch("viahtml.views.blocklist.Blocklist")
