"""Test utilities for serving content during tests."""

from contextlib import contextmanager
from multiprocessing import Process
from wsgiref.simple_server import make_server


def threaded_context(function):
    """Run a function in a separate process as a context manager.

    This will start the given function in separate process, yield, and then
    terminate the process.
    """

    @contextmanager
    def inner(*args, **kwargs):
        worker = Process(target=function, args=args, kwargs=kwargs)
        worker.start()

        yield

        worker.terminate()

    return inner


@threaded_context
def serve_content(content, content_type="text/html", port=8197, extra_headers=None):
    """Serve some given content forever with a simple HTTP server.

    :param content: Content to serve to GET requests
    :param content_type: Mime type to return for content
    :param port: Port to serve content on
    :param extra_headers: A dict of headers to add to the response
    """

    def simple_app(_environ, start_response):
        headers = [("Content-type", f"{content_type}; charset=utf-8")]
        headers.extend(extra_headers.items())

        start_response("200 OK", headers)

        return [content.encode("utf-8")]

    with make_server(host="", port=port, app=simple_app) as httpd:
        httpd.serve_forever()
