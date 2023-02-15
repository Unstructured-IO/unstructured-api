from fastapi.testclient import TestClient


from prepline_general.api.app import app


def test_general_api_health_check():
    client = TestClient(app)
    response = client.get("/healthcheck")

    assert response.status_code == 200
