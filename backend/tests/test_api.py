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


def test_financial_records_are_isolated_between_accounts(client):
    # The fixture authenticates the first account before yielding the client.
    first_transaction = client.post("/api/transactions", json={
        "title": "Private salary",
        "amount": 4200,
        "type": "income",
        "category": "Salary",
        "date": date.today().isoformat(),
    })
    assert first_transaction.status_code == 201
    transaction_id = first_transaction.json()["id"]

    first_budget = client.post("/api/budgets", json={"category": "Housing", "limit": 1200})
    assert first_budget.status_code == 201

    first_goal = client.post("/api/goals", json={"name": "Private goal", "target_amount": 5000})
    assert first_goal.status_code == 201
    goal_id = first_goal.json()["id"]

    second_account = client.post("/api/auth/register", json={
        "email": "second@example.com",
        "password": "another-secure-pass",
    })
    assert second_account.status_code == 201
    first_token = client.headers["Authorization"]
    client.headers["Authorization"] = f"Bearer {second_account.json()['access_token']}"

    assert client.get("/api/transactions").json() == []
    assert client.get("/api/budgets").json() == []
    assert client.get("/api/goals").json() == []

    summary = client.get("/api/summary")
    assert summary.status_code == 200
    assert summary.json()["balance"] == 0
    assert summary.json()["income"] == 0
    assert summary.json()["expenses"] == 0

    exported = client.get("/api/export/transactions")
    assert exported.status_code == 200
    assert "Private salary" not in exported.text

    # Account two cannot mutate account one's records by guessing their IDs.
    assert client.delete(f"/api/transactions/{transaction_id}").status_code == 404
    assert client.post(f"/api/goals/{goal_id}/contribute", json={"amount": 100}).status_code == 404

    # The same budget category is valid in a separate account.
    second_budget = client.post("/api/budgets", json={"category": "Housing", "limit": 800})
    assert second_budget.status_code == 201

    # Switching back confirms the original account's records remain intact.
    client.headers["Authorization"] = first_token
    assert [item["id"] for item in client.get("/api/transactions").json()] == [transaction_id]
    assert [item["category"] for item in client.get("/api/budgets").json()] == ["Housing"]
    assert client.get("/api/goals").json()[0]["id"] == goal_id
    assert client.get("/api/goals").json()[0]["saved_amount"] == 0
