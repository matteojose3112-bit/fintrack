import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, get_db
from app.main import app, limiter


@pytest.fixture()
def client(request):
    limiter.reset()
    original_key_func = limiter._key_func
    limiter._key_func = lambda req: req.headers.get("X-Test-Client", "testclient")
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.headers["X-Test-Client"] = request.node.name
        registered = test_client.post("/api/auth/register", json={"email": "tester@example.com", "password": "securepass123"})
        assert registered.status_code == 201
        test_client.headers["Authorization"] = f"Bearer {registered.json()['access_token']}"
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    limiter._key_func = original_key_func
    limiter.reset()
