import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.app import app as flask_app
from app.infrastructure.models import Base, UomProduct, ProductInventory

from app.infrastructure import db as db_mod


@pytest.fixture(scope="session", autouse=True)
def _setup_path():
    """Add app/ to sys.path and set test DB env var before any imports."""
    project_root = Path(__file__).resolve().parents[1]
    app_dir = project_root / "app"
    sys.path.insert(0, str(app_dir))
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    yield
    try:
        sys.path.remove(str(app_dir))
    except ValueError:
        pass


@pytest.fixture
def engine():
    """Create a fresh in-memory SQLite engine with StaticPool for test isolation."""
    e = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(e)
    yield e
    Base.metadata.drop_all(e)


@pytest.fixture
def session(engine):
    """Provide a DB session that rolls back after each test."""
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.rollback()
    sess.close()


@pytest.fixture
def client(engine, session, monkeypatch):
    """Flask test client wired to the test database."""
    monkeypatch.setattr(db_mod, "get_session", lambda: session)

    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ── Seed helpers ──────────────────────────────────────────────────────────


def seed_inventory(session, customer_id, sku, uom, quantity, location):
    inv = ProductInventory(
        customer_id=customer_id,
        sku=sku,
        uom=uom,
        quantity=quantity,
        location_identifier=location,
    )
    session.add(inv)
    session.flush()
    return inv


def seed_uom(session, customer_id, sku, uom, ea_qty):
    mapping = UomProduct(
        customer_id=customer_id,
        sku=sku,
        uom=uom,
        ea_qty=ea_qty,
    )
    session.add(mapping)
    session.flush()
    return mapping
