def test_routing_view_is_connected_correctly(app):
    response = app.get("/")

    assert response.status_code == 307
    assert response.headers["Location"]
