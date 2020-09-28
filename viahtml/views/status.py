import json

from werkzeug.wsgi import get_path_info


class StatusView:
    def __call__(self, environ, start_response):
        path = get_path_info(environ).rstrip("/")

        if path != "/_status":
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
