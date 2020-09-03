"""The application providing a WSGI entry-point."""

from gevent.monkey import patch_all

patch_all()  # This needs to happen before we load other classes

# Our job here is to leave this `application` attribute laying around as
# it's what uWSGI expects to find.
from viahtml.app import Application  # pylint: disable=wrong-import-position

application = Application.create()  # pylint: disable=invalid-name
