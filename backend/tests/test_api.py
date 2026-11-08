from datetime import date

def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_transaction_lifecycle_and_summary(client):
    payload = {
        "title": "Monthly salary",
        "amount": 2500,
        "type": "income",
        "category": "Salary",
        "date": date.today().isoformat(),
    }
    created = client.post("/api/transactions", json=payload)
    assert created.status_code == 201
    transaction = created.json()
    assert transaction["title"] == payload["title"]
    assert transaction["amount"] == payload["amount"]

    expense = {**payload, "title": "Groceries", "amount": 350, "type": "expense", "category": "Food"}
    assert client.post("/api/transactions", json=expense).status_code == 201

    listed = client.get("/api/transactions")
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    summary = client.get("/api/summary").json()
    assert summary["income"] == 2500
    assert summary["expenses"] == 350
    assert summary["balance"] == 2150
    assert summary["savings_rate"] == 86.0
    assert summary["categories"] == [{"category": "Food", "amount": 350.0}]

    deleted = client.delete(f"/api/transactions/{transaction['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted": transaction["id"]}
    assert len(client.get("/api/transactions").json()) == 1


def test_transaction_validation_and_missing_delete(client):
    invalid = client.post("/api/transactions", json={
        "title": "Invalid", "amount": -5, "type": "expense",
        "category": "Other", "date": date.today().isoformat(),
    })
    assert invalid.status_code == 422
    missing = client.delete("/api/transactions/999")
    assert missing.status_code == 404


def test_budget_creation_and_duplicate_protection(client):
    payload = {"category": "Food", "limit": 500}
    created = client.post("/api/budgets", json=payload)
    assert created.status_code == 201
    assert created.json()["category"] == "Food"
    assert created.json()["limit"] == 500
    assert created.json()["spent"] == 0

    duplicate = client.post("/api/budgets", json=payload)
    assert duplicate.status_code == 409
    assert len(client.get("/api/budgets").json()) == 1


def test_savings_goal_and_contribution(client):
    created = client.post("/api/goals", json={"name": "Emergency fund", "target_amount": 1000})
    assert created.status_code == 201
    goal_id = created.json()["id"]
    assert created.json()["saved_amount"] == 0

    contribution = client.post(f"/api/goals/{goal_id}/contribute", json={"amount": 125})
    assert contribution.status_code == 200
    assert contribution.json()["saved_amount"] == 125
    assert len(client.get("/api/goals").json()) == 1

    missing = client.post("/api/goals/999/contribute", json={"amount": 10})
    assert missing.status_code == 404


def test_csv_export(client):
    client.post("/api/transactions", json={
        "title": "Consulting", "amount": 800, "type": "income",
        "category": "Work", "date": date.today().isoformat(),
    })
    response = client.get("/api/export/transactions")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Date,Description,Type,Category,Amount" in response.text
    assert "Consulting" in response.text



def test_csv_export_escapes_spreadsheet_formulas(client):
    client.post("/api/transactions", json={
        "title": "=HYPERLINK(\"https://example.com\",\"open\")",
        "amount": 25,
        "type": "expense",
        "category": "+SUM(1,2)",
        "date": date.today().isoformat(),
    })

    response = client.get("/api/export/transactions")
    assert response.status_code == 200
    assert "'=HYPERLINK" in response.text
    assert "'+SUM" in response.text
