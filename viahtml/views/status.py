"""The status end-point for health checks."""

import json


class StatusView:
    """Status end-point."""

    def __call__(self, path, environ, start_response):
        """Provide a status response if required.

        :param path: The url path of the request
        :param environ: WSGI environ dict
        :param start_response: WSGI `start_response()` function
        :return: An iterator of content if required or None
        """
        if path.rstrip("/") != "/_status":
            # We don't want to handle this call
            return None

        return self._json_response(
            start_response,
            status_line="200 OK",
            headers={"Cache-Control": "no-cache"},
            body={"status": "okay"},
        )

    @classmethod
    def _json_response(cls, start_response, status_line, headers, body):
        headers.setdefault("Content-Type", "application/json; charset=utf-8")

        start_response(status_line, list(headers.items()))

        return [json.dumps(body).encode("utf-8")]
