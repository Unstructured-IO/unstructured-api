from fastapi.testclient import TestClient


from prepline_emails.api.app import app


def test_emails_api_health_check():
    client = TestClient(app)
    response = client.get("/healthcheck")

    assert response.status_code == 200
