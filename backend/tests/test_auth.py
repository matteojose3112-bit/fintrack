from datetime import date


def test_register_login_and_current_user(client):
    client.headers.pop("Authorization")
    registered = client.post("/api/auth/register", json={"email": "new@example.com", "password": "securepass123"})
    assert registered.status_code == 201
    token = registered.json()["access_token"]
    assert registered.json()["user"]["email"] == "new@example.com"

    client.headers["Authorization"] = f"Bearer {token}"
    current = client.get("/api/auth/me")
    assert current.status_code == 200
    assert current.json()["email"] == "new@example.com"

    logged_in = client.post("/api/auth/login", data={"username": "new@example.com", "password": "securepass123"})
    assert logged_in.status_code == 200
    assert logged_in.json()["user"]["email"] == "new@example.com"


def test_registration_validation_and_duplicate_email(client):
    client.headers.pop("Authorization")
    assert client.post("/api/auth/register", json={"email": "invalid", "password": "securepass123"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "weak@example.com", "password": "short"}).status_code == 422
    duplicate = client.post("/api/auth/register", json={"email": "tester@example.com", "password": "securepass123"})
    assert duplicate.status_code == 409


def test_financial_routes_require_authentication(client):
    client.headers.pop("Authorization")
    assert client.get("/api/summary").status_code == 401
    assert client.get("/api/transactions").status_code == 401
    assert client.post("/api/budgets", json={"category": "Food", "limit": 100}).status_code == 401


def test_financial_records_are_isolated_between_users(client):
    original_token = client.headers["Authorization"]
    client.post("/api/transactions", json={
        "title": "Private salary", "amount": 900, "type": "income",
        "category": "Work", "date": date.today().isoformat(),
    })
    second = client.post("/api/auth/register", json={"email": "second@example.com", "password": "securepass123"})
    client.headers["Authorization"] = f"Bearer {second.json()['access_token']}"
    assert client.get("/api/transactions").json() == []
    assert client.get("/api/summary").json()["balance"] == 0
    client.post("/api/budgets", json={"category": "Food", "limit": 200})
    client.headers["Authorization"] = original_token
    assert len(client.get("/api/transactions").json()) == 1
    assert client.get("/api/budgets").json() == []


def test_login_rejects_excessive_urlencoded_form_fields(client):
    fields = [
        ("username", "tester@example.com"),
        ("password", "incorrect-password"),
        *((f"extra_{index}", "x") for index in range(999)),
    ]
    body = "&".join(f"{key}={value}" for key, value in fields)
    response = client.post(
        "/api/auth/login",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 400
