from fastapi.testclient import TestClient


def test_flask_token_in_fastapi(app, fastapi_app, setup_test_db):
    with app.test_client() as flask_client:
        flask_response = flask_client.post(
            "/api/auth/login",
            json={"username": "testadmin", "password": "admin123"},
        )
        assert flask_response.status_code == 200
        flask_token = flask_response.get_json()["access_token"]

    with TestClient(fastapi_app) as fastapi_client:
        fastapi_response = fastapi_client.get(
            "/api/v2/auth/me",
            headers={"Authorization": f"Bearer {flask_token}"},
        )
        assert fastapi_response.status_code == 200
        assert fastapi_response.json()["username"] == "testadmin"


def test_fastapi_token_in_flask(app, fastapi_app, setup_test_db):
    with TestClient(fastapi_app) as fastapi_client:
        fastapi_response = fastapi_client.post(
            "/api/v2/auth/login",
            json={"username": "testadmin", "password": "admin123"},
        )
        assert fastapi_response.status_code == 200
        fastapi_token = fastapi_response.json()["access_token"]

    with app.test_client() as flask_client:
        flask_response = flask_client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {fastapi_token}"},
        )
        assert flask_response.status_code == 200
        assert flask_response.get_json()["user"]["username"] == "testadmin"
