"""The robots.txt endpoint."""


class RobotsView:
    """robots.txt endpoint."""

    def __call__(self, path, environ, start_response):
        """Provide a robots.txt response if required.

        :param path: the URL path of the request
        :param environ: the WSGI environ dict
        :param start_response: the WSGI start_response() function
        :return: the response body content
        :rtype: bytes
        """
        if path.rstrip("/") != "/robots.txt":
            return None

        start_response(
            "200 OK",
            [
                ("Cache-Control", "public, max-age=1800"),
                ("Content-Type", "text/plain"),
            ],
        )

        return "User-agent: * \nDisallow: /".encode("utf-8")
