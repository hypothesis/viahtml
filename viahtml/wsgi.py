"""The application providing a WSGI entry-point."""

import os

# Our job here is to leave this `application` attribute laying around as
# it's what uWSGI expects to find.
from viahtml.app import Application

application = Application()

if os.environ.get("SENTRY_DSN"):  # pragma: no cover
    # As both pywb and sentry shamelessly monkey patch gevent etc the order
    # of imports matter. Importing sentry here results in the right patching.
    import sentry_sdk
    from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

    # pylint: disable=redefined-variable-type
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])
    application = SentryWsgiMiddleware(application)
