from pywb.apps.frontendapp import FrontEndApp


def test_it_exports_application():
    # For fixtures to kick in we need to import this here, as all the work
    # happens instantly
    from viahtml.wsgi import application  # pylint: disable=import-outside-toplevel

    assert isinstance(application, FrontEndApp)
