# pylint:disable=protected-access

from unittest.mock import create_autospec, patch, sentinel

import pytest
from pywb.rewrite.content_rewriter import RewriteInfo
from pywb.rewrite.default_rewriter import DefaultRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

from viahtml.hooks import Hooks
from viahtml.patch import (
    ESM_MOD,
    ESM_TEXT_TYPE,
    _ESMWombatProxyRewriter,
    _patch_esm_rewriting,
    _PatchedHTMLRewriter,
    _resolve_text_type,
)


class TestRewriteLinkHref:
    @pytest.mark.parametrize(
        "original_value,tag_attrs,expected_value",
        [
            # It rewrites links that have a rel="manifest" attribute to go through
            # pywb's /id_/<URL> endpoint in order to disable any rewriting of
            # manifest files.
            ("https://example.com", [("rel", "manifest")], "id_/https://example.com"),
            # Links that preload an ES module go through the module modifier, so
            # that the module isn't served with pywb's classic script wrapper.
            (
                "https://example.com",
                [("rel", "modulepreload")],
                "esm_/https://example.com",
            ),
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

    def test_it_sends_module_scripts_to_the_module_modifier(
        self, patched_html_rewriter
    ):
        self.returning_module_script(patched_html_rewriter)

        patched_html_rewriter._rewrite_tag_attrs("script", sentinel.tag_attrs)

        assert (
            self.written(patched_html_rewriter)
            == '<script type="module" src="esm_/https://example.com/app.js"'
        )

    def test_it_restores_the_script_modifier_afterwards(self, patched_html_rewriter):
        self.returning_module_script(patched_html_rewriter)
        original = patched_html_rewriter.rewrite_tags["script"]

        patched_html_rewriter._rewrite_tag_attrs("script", sentinel.tag_attrs)

        assert patched_html_rewriter.rewrite_tags["script"] == original

    def test_it_restores_the_script_modifier_if_pywb_raises(
        self, patched_html_rewriter
    ):
        self.returning_module_script(patched_html_rewriter)
        original = patched_html_rewriter.rewrite_tags["script"]

        with patch.object(HTMLRewriter, "_rewrite_tag_attrs", side_effect=RuntimeError):
            with pytest.raises(RuntimeError):
                patched_html_rewriter._rewrite_tag_attrs("script", sentinel.tag_attrs)

        assert patched_html_rewriter.rewrite_tags["script"] == original

    def returning_module_script(self, patched_html_rewriter):
        """Make the hook return a `<script type="module">` with stop=False."""
        patched_html_rewriter.hooks.modify_tag_attrs.return_value = (
            [("type", "module"), ("src", "https://example.com/app.js")],
            False,
        )

    def written(self, patched_html_rewriter):
        """Return everything that was written to out.write() as one string."""
        return "".join(
            call[0][0] for call in patched_html_rewriter.out.write.call_args_list
        )


class TestIsModuleScript:
    @pytest.mark.parametrize(
        "tag,tag_attrs,expected",
        [
            ("script", [("type", "module")], True),
            # The type is matched case- and whitespace-insensitively.
            ("script", [("type", " Module ")], True),
            # Classic scripts, whether they declare a type or not.
            ("script", [("type", "text/javascript")], False),
            ("script", [("src", "app.js")], False),
            ("script", [("type", None)], False),
            # Only <script> tags can load a module this way.
            ("link", [("type", "module")], False),
        ],
    )
    def test_it(self, patched_html_rewriter, tag, tag_attrs, expected):
        assert patched_html_rewriter._is_module_script(tag, tag_attrs) is expected


class TestESMWombatProxyRewriter:
    def test_it_declares_the_same_objects_as_pywb(self, esm_rewriter):
        for obj in esm_rewriter.local_objs:
            assert f'let {obj} = _____WB$wombat$assign$function_____("{obj}");' in (
                esm_rewriter.first_buff
            )

    @pytest.mark.parametrize(
        "forbidden,reason",
        [
            ("let arguments;", "strict mode, which modules always use, forbids it"),
            ("{", "a block would enclose the module's export statement"),
        ],
    )
    def test_it_omits_what_a_module_rejects(self, esm_rewriter, forbidden, reason):
        declarations = esm_rewriter.first_buff.split("let window")[1]

        assert forbidden not in declarations, reason

    def test_it_appends_nothing(self, esm_rewriter):
        # pywb appends '}}' to close the block it opened. There's no block here.
        assert not esm_rewriter.last_buff

    def test_it_reads_the_global_object_before_shadowing_it(self, esm_rewriter):
        # The statements above the declarations share their scope, so reading
        # `self` there would hit the temporal dead zone of `let self`.
        preamble = esm_rewriter.first_buff.split("let window")[0]

        assert "self." not in preamble
        assert "globalThis." in preamble

    @pytest.fixture
    def esm_rewriter(self):
        return _ESMWombatProxyRewriter(UrlRewriter("wburl"))


class TestResolveTextType:
    def test_it_reports_modules_as_such(self):
        response = self.response_for(f"{ESM_MOD}/https://example.com/app.js")

        assert _resolve_text_type(response, "js") == ESM_TEXT_TYPE

    def test_it_leaves_everything_else_to_pywb(self):
        response = self.response_for("js_/https://example.com/app.js")

        with patch("viahtml.patch._PYWB_RESOLVE_TEXT_TYPE") as pywb_resolve_text_type:
            returned = _resolve_text_type(response, sentinel.text_type)

        pywb_resolve_text_type.assert_called_once_with(response, sentinel.text_type)
        assert returned == pywb_resolve_text_type.return_value

    def response_for(self, wburl):
        response = create_autospec(RewriteInfo, instance=True)
        response.url_rewriter = UrlRewriter(wburl)
        return response


@pytest.mark.usefixtures("unpatched_pywb")
class TestPatchESMRewriting:
    def test_it_registers_the_rewriter(self):
        _patch_esm_rewriting()

        assert (
            DefaultRewriter.DEFAULT_REWRITERS[ESM_TEXT_TYPE] is _ESMWombatProxyRewriter
        )

    def test_it_replaces_pywbs_text_type_resolution(self):
        _patch_esm_rewriting()

        assert RewriteInfo._resolve_text_type is _resolve_text_type

    def test_applying_it_twice_is_the_same_as_once(self):
        _patch_esm_rewriting()
        _patch_esm_rewriting()

        # A patch which wrapped whatever it found would stack on each call.
        assert RewriteInfo._resolve_text_type is _resolve_text_type

    @pytest.fixture
    def unpatched_pywb(self):
        """Undo the patch for the duration of the test, and put it back after."""
        resolve_text_type = RewriteInfo._resolve_text_type
        rewriters = dict(DefaultRewriter.DEFAULT_REWRITERS)
        DefaultRewriter.DEFAULT_REWRITERS.pop(ESM_TEXT_TYPE, None)

        yield

        RewriteInfo._resolve_text_type = resolve_text_type
        DefaultRewriter.DEFAULT_REWRITERS.clear()
        DefaultRewriter.DEFAULT_REWRITERS.update(rewriters)


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
