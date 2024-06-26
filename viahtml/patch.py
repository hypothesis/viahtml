"""Tools to apply the hooks to a running `pywb` app."""

from typing import Optional

from pywb.apps.rewriterapp import RewriterApp
from pywb.rewrite.default_rewriter import DefaultRewriter
from pywb.rewrite.html_rewriter import HTMLRewriter
from pywb.rewrite.url_rewriter import UrlRewriter

from viahtml.hooks import Hooks


def apply_post_app_hooks(rewriter_app, hooks: Hooks):
    """Apply hooks after the app has been instantiated."""
    _PatchedRewriterApp.patch(rewriter_app, hooks)


def apply_pre_app_hooks(hooks: Hooks):
    """Apply hooks before the app has been instantiated."""

    _patch_url_rewriter(hooks)
    _PatchedHTMLRewriter.patch(hooks)


def _patch_url_rewriter(hooks: Hooks):
    # Modify the list of prefixes that prevent a URL from being rewritten
    prefixes = list(UrlRewriter.NO_REWRITE_URI_PREFIX)
    prefixes.extend(hooks.ignore_prefixes)
    UrlRewriter.NO_REWRITE_URI_PREFIX = tuple(prefixes)


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

        # If the hook returns stop=False we go on to all pywb's default
        # _rewrite_tag_attrs with the new attrs returned by the hook.
        return super()._rewrite_tag_attrs(tag, new_attrs, set_parsing_context)


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
