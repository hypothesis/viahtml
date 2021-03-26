import json


def test_status_view_is_connected_correctly(app):
    response = app.get("/_status")

    assert json.loads(response.body) == {"status": "okay"}
