"""Test muhiti: alohida `uniload_test` bazasi, toza sxema, migratsiyalar, bootstrap va demo seed.

Ilova testlarda ham cheklangan `uniload_app` roli bilan ulanadi — shuning uchun RLS haqiqiy
holatda tekshiriladi.
"""

import os
import uuid

os.environ.setdefault("UNILOAD_ENV", "test")
os.environ.setdefault("UNILOAD_DATABASE_URL",
                      "postgresql+psycopg://uniload_app:uniload_app@localhost:5433/uniload_test")
os.environ.setdefault("UNILOAD_MIGRATION_DATABASE_URL",
                      "postgresql+psycopg://uniload:uniload@localhost:5433/uniload_test")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app import cli  # noqa: E402
from app.core.config import get_settings  # noqa: E402

PASSWORD = "Demo12345!"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def database():
    owner_url = get_settings().migration_database_url
    engine = create_engine(owner_url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    engine.dispose()

    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["url"] = owner_url
    command.upgrade(cfg, "head")
    with Session(create_engine(owner_url)) as db:
        cli.bootstrap(db)
        cli.seed(db, PASSWORD)
    yield


@pytest.fixture(scope="session")
def client() -> TestClient:
    from app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def owner_db():
    """Jadval egasi sessiyasi (RLS chetlab o‘tiladi) — faqat test tayyorlash va tekshirish uchun."""
    with Session(create_engine(get_settings().migration_database_url)) as db:
        yield db


def login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def email_for(role_prefix: str, uni: str = "demo-tu") -> str:
    return f"{role_prefix}@{uni}.uniload.example"


@pytest.fixture(scope="session")
def tu_admin(client):
    return login(client, email_for("admin"))


@pytest.fixture(scope="session")
def tu_office(client):
    return login(client, email_for("oquv"))


@pytest.fixture(scope="session")
def tu_head(client):
    return login(client, email_for("kafedra"))


@pytest.fixture(scope="session")
def tu_teacher(client):
    return login(client, email_for("oqituvchi"))


@pytest.fixture(scope="session")
def pu_office(client):
    return login(client, email_for("oquv", "demo-pu"))


@pytest.fixture(scope="session")
def pu_admin(client):
    return login(client, email_for("admin", "demo-pu"))


@pytest.fixture(scope="session")
def super_admin(client):
    return login(client, "superadmin@uniload.example")


@pytest.fixture
def unique() -> str:
    return uuid.uuid4().hex[:8]


def university_id(owner_db: Session, code: str) -> uuid.UUID:
    from app.modules.tenants.models import University
    return owner_db.scalar(select(University.id).where(University.code == code))


_next_year = iter(range(2031, 2100, 2))  # +1 yil nusxa testlari uchun bo‘sh qoladi


@pytest.fixture
def free_year() -> int:
    """Testlar bir-biriga xalaqit bermasligi uchun har biriga alohida yil."""
    return next(_next_year)
