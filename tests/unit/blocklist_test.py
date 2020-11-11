import os

import pytest

from viahtml.blocklist import Blocklist


class TestBlocklist:
    def test_it_can_start_without_a_file(self):
        blocklist = Blocklist("missing.txt")

        assert blocklist.domains == {}

    def test_it_reloads_when_the_file_changes(self, blocklist_file):
        blocklist = Blocklist(blocklist_file)
        assert blocklist.domains  # Check we've loaded something
        blocklist.domains = {}
        blocklist_file.touch()  # Reset the access times

        blocklist.is_blocked("foo")

        # The original set has not been reloaded
        assert blocklist.domains

    def test_it_does_not_reload_if_the_file_is_the_same(self, blocklist_file):
        blocklist = Blocklist(blocklist_file)
        assert blocklist.domains  # Check we've loaded something
        blocklist.domains = {}

        blocklist.is_blocked("foo")

        # The original set has not been reloaded
        assert blocklist.domains == {}

    @pytest.mark.parametrize(
        "line,reason",
        (
            ("example.com publisher-blocked", Blocklist.Reason.PUBLISHER_BLOCKED),
            ("example.com malicious", Blocklist.Reason.MALICIOUS),
            ("   example.com    media-mixed   ", Blocklist.Reason.MEDIA_MIXED),
            (
                "example.com media-image   # trailing comment",
                Blocklist.Reason.MEDIA_IMAGE,
            ),
            ("example.com other", Blocklist.Reason.OTHER),
            ("example.com right-format-wrong-value", Blocklist.Reason.OTHER),
            # Comment
            ("# any old comment", None),
            # Unparsable
            ("example.com", None),
            ("example.com too many parts", None),
            # Allowed for viahtml
            ("example.com  media-video", None),
        ),
    )
    def test_file_loading(self, tmp_path, line, reason):
        filename = tmp_path / "blocklist.txt"
        filename.write_text(line)

        blocklist = Blocklist(filename)

        assert blocklist.domains == ({"example.com": reason} if reason else {})

    @pytest.mark.parametrize(
        "line,reason",
        (
            ("*.example.com publisher-blocked", Blocklist.Reason.PUBLISHER_BLOCKED),
            ("*.example.com rubbish", Blocklist.Reason.OTHER),
            ("*.example.com", None),
        ),
    )
    def test_file_loading_wildcards(self, tmp_path, line, reason):
        filename = tmp_path / "blocklist.txt"
        filename.write_text(line)

        blocklist = Blocklist(filename)

        if not reason:
            assert blocklist.patterns == {}
        else:
            assert len(blocklist.patterns) == 1
            ((domain, found_reason),) = blocklist.patterns.items()
            assert found_reason == reason
            assert domain.pattern == r"^.*\.example\.com$"

    @pytest.mark.parametrize(
        "url,expected_blocked",
        (
            ("https://www.example.com", True),
            ("http://www.example.com", True),
            ("//www.example.com", True),
            ("www.example.com", True),
            ("http://www.example.com/path", True),
            ("http://www.example.com/path?a=b", True),
            # Sub-domains don't count
            ("http://example.com", False),
            ("http://example.org", False),
            # Wildcard matching
            ("anything.example.net", True),
            ("anything.nested.example.net", True),
            ("thisisfineexample.net", False),
        ),
    )
    def test_url_matching(self, url, expected_blocked):
        blocklist = Blocklist("missing.txt")
        blocklist.add_domain("www.example.com", Blocklist.Reason.OTHER)
        blocklist.add_domain("*.example.net", Blocklist.Reason.OTHER)

        assert bool(blocklist.is_blocked(url)) == expected_blocked

    @pytest.fixture
    def blocklist_file(self, tmp_path):
        blocklist_file = tmp_path / "blocklist.txt"
        blocklist_file.write_text("example.com other")

        # Make the file very old
        os.utime(blocklist_file, (0, 0))

        return blocklist_file
