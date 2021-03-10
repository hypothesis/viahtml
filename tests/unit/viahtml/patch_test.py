# pylint:disable=protected-access

from unittest.mock import create_autospec, sentinel

import pytest
from pywb.rewrite.url_rewriter import UrlRewriter

from viahtml.hooks import Hooks
from viahtml.patch import _PatchedHTMLRewriter


class TestRewriteLinkHref:
    @pytest.mark.parametrize(
        "original_value,tag_attrs,expected_value",
        [
            # It rewrites links that have a rel="manifest" attribute to go through
            # pywb's /id_/<URL> endpoint in order to disable any rewriting of
            # manifest files.
            ("https://example.com", [("rel", "manifest")], "id_/https://example.com"),
            # Any other links get sent to the rw_mod endpoint which will rewrite
            # the file as usual.
            ("https://example.com", [], "rw_mod/https://example.com"),
        ],
    )
    def test_it(self, patched_html_rewriter, original_value, tag_attrs, expected_value):
        returned_value = patched_html_rewriter._rewrite_link_href(
            original_value,
            tag_attrs,
            "rw_mod",
        )

        assert returned_value == expected_value


class TestRewriteTagAttrs:
    def test_rewrite_tag_attrs_calls_modify_tag_attrs(self, patched_html_rewriter):
        patched_html_rewriter._rewrite_tag_attrs("script", sentinel.tag_attrs)

        patched_html_rewriter.hooks.modify_tag_attrs.assert_called_once_with(
            "script", sentinel.tag_attrs
        )

    def test_rewrite_tag_attrs_if_modify_tag_attrs_returns_stop_True(
        self, patched_html_rewriter
    ):
        returned = patched_html_rewriter._rewrite_tag_attrs(
            "script", sentinel.tag_attrs
        )

        # It writes out the tag and its modified attributes as returned by modify_tag_attrs().
        # Because modify_tag_attrs() returned stop=True pywb's
        # _rewrite_tag_attrs() wasn't called so the script.js URL wasn't
        # rewritten.
        assert (
            self.written(patched_html_rewriter)
            == '<script src="https://example.com/script.js" async referrerpolicy="no-referrer"'
        )
        # It returns True. Not sure why it has to do this.
        assert returned is True

    def test_rewrite_tag_attrs_if_modify_tag_attrs_returns_stop_False(
        self, patched_html_rewriter
    ):
        # Make modify_tag_attrs() return the same modified attrs but with stop=False.
        patched_html_rewriter.hooks.modify_tag_attrs.return_value = (
            patched_html_rewriter.hooks.modify_tag_attrs.return_value[0],
            False,
        )

        returned = patched_html_rewriter._rewrite_tag_attrs(
            "script", sentinel.tag_attrs
        )

        # It writes out the tag and its modified attributes.
        #
        # Because modify_tag_attrs() returned stop=False pywb's
        # _rewrite_tag_attrs() *was* called so the script.js URL was
        # rewritten to start with js_/.
        #
        # The modified async and referrerpolicy attrs returned by
        # modify_tag_attrs() were passed to pywb's _rewrite_tag_attrs() so they
        # did get written out.
        assert (
            self.written(patched_html_rewriter)
            == '<script src="js_/https://example.com/script.js" async referrerpolicy="no-referrer"'
        )
        # It returns what pywb's _rewrite_tag_attrs returned.
        assert returned is True

    def written(self, patched_html_rewriter):
        """Return everything that was written to out.write() as one string."""
        return "".join(
            call[0][0] for call in patched_html_rewriter.out.write.call_args_list
        )


@pytest.fixture
def patched_html_rewriter():
    patched_html_rewriter = _PatchedHTMLRewriter(UrlRewriter("wburl"))
    patched_html_rewriter.hooks = create_autospec(Hooks, instance=True, spec_set=True)
    patched_html_rewriter.hooks.modify_tag_attrs.return_value = (
        # The modified tag attributes returned by our modify_tag_attrs() hook.
        [
            ("src", "https://example.com/script.js"),
            ("async", None),
            ("referrerpolicy", "no-referrer"),
        ],
        # By default modify_tag_attrs() returns stop=True which tells the patch
        # to *not* call pywb's original _rewrite_tag_attrs() method.
        True,
    )

    class Out:
        def write(self, s):
            """Write a string out to the client."""

    patched_html_rewriter.out = create_autospec(Out, instance=True, spec_set=True)
    return patched_html_rewriter
