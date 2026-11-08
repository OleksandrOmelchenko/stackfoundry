from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_order():
    response = client.get("/orders/1", headers={"X-Customer-Id": "alice"})
    assert response.status_code == 200
