"""Tools to apply the hooks to a running `pywb` app."""

from typing import Optional

from pywb.apps.rewriterapp import RewriterApp
from pywb.rewrite.content_rewriter import RewriteInfo
from pywb.rewrite.default_rewriter import DefaultRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.regex_rewriters import JSWombatProxyRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

from viahtml.hooks import Hooks

# Our own URL modifier and text type for JS the page loads as an ES module.
# `pywb` has neither: every script is a classic one as far as it's concerned.
ESM_MOD = "esm_"
ESM_TEXT_TYPE = "js-esm"

# Stands in for `pywb`'s own `rewrite_tags["script"]`, which maps `src` to the
# classic JS modifier whatever the script's type.
ESM_SCRIPT_TAGS = {"src": ESM_MOD, "xlink:href": ESM_MOD}


def apply_post_app_hooks(rewriter_app, hooks: Hooks):
    """Apply hooks after the app has been instantiated."""
    _PatchedRewriterApp.patch(rewriter_app, hooks)


def apply_pre_app_hooks(hooks: Hooks):
    """Apply hooks before the app has been instantiated."""

    _patch_url_rewriter(hooks)
    _patch_esm_rewriting()
    _PatchedHTMLRewriter.patch(hooks)


def _patch_url_rewriter(hooks: Hooks):
    # Modify the list of prefixes that prevent a URL from being rewritten
    prefixes = list(UrlRewriter.NO_REWRITE_URI_PREFIX)
    prefixes.extend(hooks.ignore_prefixes)
    UrlRewriter.NO_REWRITE_URI_PREFIX = tuple(prefixes)


class _ESMWombatProxyRewriter(JSWombatProxyRewriter):
    """Serve an ES module with wombat's proxies set up.

    So that wombat can proxy `window`, `location` and the rest, `pywb` wraps
    every script it serves in a block which redeclares them. A module won't
    parse with that wrapper and the browser discards the file without running
    a line of it, so two of its parts go:

    * `let arguments`. Strict mode forbids it, and modules are always strict.
    * The block. A classic script's outermost scope is the global scope, so
      `pywb` needs a block to declare into. A module's is already its own, and
      a block would enclose the `export` which belongs at the top level.

    The declarations themselves stay, and shadowing is why: it leaves telling
    a variable from a property of the same name to the language. Substituting
    the references instead, as `JSLinkAndLocationRewriter` does, rewrote
    Kanopy's `document.body.style.top` along with the real thing.

    `globalThis` in the statements above the declarations keeps them from
    reading `let self` before it is initialised.
    """

    def __init__(self, rewriter, extra_rules=None):
        super().__init__(rewriter, extra_rules=extra_rules)

        self.first_buff = self._module_safe_first_buff()
        self.last_buff = ""

    def _module_safe_first_buff(self):
        init_func = "_____WB$wombat$assign$function_____"

        lines = [
            f"var {init_func} = function(name) {{ return (globalThis._wb_wombat "
            "&& globalThis._wb_wombat.local_init "
            "&& globalThis._wb_wombat.local_init(name)) || globalThis[name]; };",
            "if (!globalThis.__WB_pmw) { globalThis.__WB_pmw = function(obj) "
            "{ this.__WB_source = obj; return this; } }",
        ]
        lines += [f'let {obj} = {init_func}("{obj}");' for obj in self.local_objs]

        return "\n" + "\n".join(lines) + "\n"


_PYWB_RESOLVE_TEXT_TYPE = (
    RewriteInfo._resolve_text_type  # pylint:disable=protected-access
)


def _resolve_text_type(self, text_type):
    """Report the text type of a response, recognising ES modules.

    Replaces the `pywb` method of the same name. Everything which isn't a
    module is left to the original.
    """

    if self.url_rewriter.wburl.mod == ESM_MOD:
        return ESM_TEXT_TYPE

    return _PYWB_RESOLVE_TEXT_TYPE(self, text_type)


def _patch_esm_rewriting():
    """Serve ES modules with a wrapper they can parse.

    `_PatchedHTMLRewriter` tags module URLs with `ESM_MOD`; this teaches the
    content rewriter what to do when the browser comes back asking for one.
    """

    DefaultRewriter.DEFAULT_REWRITERS[ESM_TEXT_TYPE] = _ESMWombatProxyRewriter
    RewriteInfo._resolve_text_type = (  # pylint:disable=protected-access
        _resolve_text_type
    )


class _PatchedHTMLRewriter(HTMLRewriter):
    hooks: Optional[Hooks] = None

    @classmethod
    def patch(cls, hooks: Hooks):
        """Patch the parent object."""

        cls.hooks = hooks
        DefaultRewriter.DEFAULT_REWRITERS["html"] = _PatchedHTMLRewriter

    def _rewrite_link_href(self, attr_value, tag_attrs, rw_mod):
        # Prevent `pywb` from attempting to insert Javascript style rewriting
        # stuff into "<link rel='manifest'>" items. This fixes a bug with
        # www.theguardian.com which declares it's manifest as `text/javascript`
        rel = self.get_attr(tag_attrs, "rel")

        if rel == "manifest":
            # 'id_' type hint appears to disable any rewriting
            return self._rewrite_url(attr_value, "id_")

        if rel == "modulepreload":
            return self._rewrite_url(attr_value, ESM_MOD)

        return super()._rewrite_link_href(attr_value, tag_attrs, rw_mod)

    def _rewrite_tag_attrs(self, tag, tag_attrs, set_parsing_context=True):
        # Jump into the general tag + attr rewriting step to allow flexible
        # rewriting of tags should we need to

        new_attrs, stop = self.hooks.modify_tag_attrs(tag, tag_attrs)

        # If the hook returns stop=True we need to stop pywb's default
        # rewriting and take over writing out the response with the new_attrs
        # returned by the hook.
        if stop:
            self.out.write("<" + tag)

            for name, value in new_attrs:
                self._write_attr(
                    name=name,
                    value="" if value is None else value,
                    empty_attr=bool(value is None),
                )

            return True

        if self._is_module_script(tag, new_attrs):
            script_tags = self.rewrite_tags["script"]
            self.rewrite_tags["script"] = ESM_SCRIPT_TAGS

            try:
                return super()._rewrite_tag_attrs(tag, new_attrs, set_parsing_context)
            finally:
                self.rewrite_tags["script"] = script_tags

        # If the hook returns stop=False we go on to all pywb's default
        # _rewrite_tag_attrs with the new attrs returned by the hook.
        return super()._rewrite_tag_attrs(tag, new_attrs, set_parsing_context)

    def _is_module_script(self, tag, tag_attrs):
        if tag != "script":
            return False

        type_value = self.get_attr(tag_attrs, "type")

        return bool(type_value) and type_value.strip().lower() == "module"


class _PatchedRewriterApp(RewriterApp):
    hooks: Optional[Hooks] = None

    @classmethod
    def patch(cls, rewriter, hooks: Hooks):
        """Patch the rewriter object."""

        # Change the class of the rewriter to be this class, forcibly casting
        # it to be an instance of this class
        rewriter.__class__ = cls
        rewriter.hooks = hooks

        # Update the Jinja environment to have the vars we want
        rewriter.jinja_env.jinja_env.globals.update(hooks.template_vars)

    def render_content(self, wb_url, kwargs, environ):  # pragma: no cover
        response = super().render_content(wb_url, kwargs, environ)

        response = self.hooks.modify_render_response(response)

        return response

    def get_upstream_url(self, wb_url, kwargs, params):  # pragma: no cover
        params["url"] = self.hooks.get_upstream_url(doc_url=params["url"])

        return super().get_upstream_url(wb_url, kwargs, params)
