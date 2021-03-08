"""The application providing a WSGI entry-point."""

# Our job here is to leave this `application` attribute laying around as
# it's what uWSGI expects to find.
from viahtml.app import Application

application = Application()
