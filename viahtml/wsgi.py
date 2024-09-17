"""The application providing a WSGI entry-point."""

import os
import signal

# Our job here is to leave this `application` attribute laying around as
# it's what uWSGI expects to find.
from viahtml.app import Application


def _dump_stacks(_signal, frame):  # pylint:disable=unused-argument, # pragma: no cover
    # Print both Python thread and gevent "greenlet" stats and backtraces.
    #
    # See https://www.gevent.org/monitoring.html#visibility
    import gevent  # pylint:disable=import-outside-toplevel

    gevent.util.print_run_info()


application = Application()

if os.environ.get("SENTRY_DSN"):  # pragma: no cover
    # As both pywb and sentry shamelessly monkey patch gevent etc the order
    # of imports matter. Importing sentry here results in the right patching.
    import sentry_sdk
    from sentry_sdk.integrations.wsgi import SentryWsgiMiddleware

    # pylint: disable=redefined-variable-type
    sentry_sdk.init(dsn=os.environ["SENTRY_DSN"])
    application = SentryWsgiMiddleware(application)

# Add a way to dump stacks so we can see what a uWSGI worker is doing if it
# hangs.
#
# We use `SIGCONT` for this because this handler isn't used for anything
# important, and uWSGI defines its own `SIGUSR1` and `SIGUSR2` handlers after
# this code runs.
signal.signal(signal.SIGCONT, _dump_stacks)
