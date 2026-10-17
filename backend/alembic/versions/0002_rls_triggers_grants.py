"""RLS siyosatlari, o‘quv yili qulfi triggerlari, ilova roli huquqlari, ruxsatlar katalogi.

docs/01-arxitektura.md 1.5–1.7, docs/03-er-model.md 3.5.

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op
from app.core.permissions import PERMISSIONS
from app.db.ids import uuid7

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

APP_ROLE = "uniload_app"

# Oddiy tenant jadvallari: university_id = joriy tenant yoki platforma rejimi.
TENANT_TABLES = ["users", "user_roles", "academic_years", "semesters"]
YEAR_SCOPED_TABLES = ["semesters"]

HELPERS = """
CREATE OR REPLACE FUNCTION app_current_university() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.university_id', true), '')::uuid $$;

CREATE OR REPLACE FUNCTION app_is_platform() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT coalesce(current_setting('app.platform', true), 'off') = 'on' $$;

CREATE OR REPLACE FUNCTION app_override_reason() RETURNS text
LANGUAGE sql STABLE AS $$ SELECT NULLIF(current_setting('app.override_reason', true), '') $$;
"""

YEAR_LOCK = """
-- Tasdiqlangan/arxivlangan yilga tegishli yozuvlarni override sababisiz o‘zgartirishni taqiqlaydi.
CREATE OR REPLACE FUNCTION trg_year_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_status text;
BEGIN
  IF app_override_reason() IS NOT NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;
  IF TG_OP IN ('UPDATE', 'DELETE') THEN
    SELECT status INTO v_status FROM academic_years WHERE id = OLD.academic_year_id;
    IF v_status IN ('approved', 'archived') THEN
      RAISE EXCEPTION 'O‘quv yili "%" holatida — o‘zgartirish taqiqlangan', v_status USING ERRCODE = 'UL001';
    END IF;
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') THEN
    SELECT status INTO v_status FROM academic_years WHERE id = NEW.academic_year_id;
    IF v_status IN ('approved', 'archived') THEN
      RAISE EXCEPTION 'O‘quv yili "%" holatida — o‘zgartirish taqiqlangan', v_status USING ERRCODE = 'UL001';
    END IF;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;

-- academic_years jadvalining o‘zi: qulflangan yilda faqat ruxsat etilgan holat o‘tishlari.
CREATE OR REPLACE FUNCTION trg_academic_year_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF app_override_reason() IS NOT NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;
  IF TG_OP = 'DELETE' THEN
    IF OLD.status IN ('approved', 'archived') THEN
      RAISE EXCEPTION 'Tasdiqlangan yoki arxivlangan o‘quv yilini o‘chirib bo‘lmaydi' USING ERRCODE = 'UL001';
    END IF;
    RETURN OLD;
  END IF;
  IF OLD.status IN ('approved', 'archived') THEN
    IF (NEW.start_year, NEW.starts_on, NEW.ends_on, NEW.source_year_id, NEW.university_id)
       IS DISTINCT FROM (OLD.start_year, OLD.starts_on, OLD.ends_on, OLD.source_year_id, OLD.university_id) THEN
      RAISE EXCEPTION 'O‘quv yili "%" holatida — ma’lumotlarini o‘zgartirib bo‘lmaydi', OLD.status
        USING ERRCODE = 'UL001';
    END IF;
    IF OLD.status = 'archived' AND NEW.status <> 'archived' THEN
      RAISE EXCEPTION 'Arxivlangan o‘quv yilini qayta ochib bo‘lmaydi' USING ERRCODE = 'UL001';
    END IF;
    IF OLD.status = 'approved' AND NEW.status NOT IN ('approved', 'archived') THEN
      RAISE EXCEPTION 'Tasdiqlangan o‘quv yilini faqat arxivlash mumkin' USING ERRCODE = 'UL001';
    END IF;
  END IF;
  RETURN NEW;
END $$;
"""


def _tenant_policy(table: str) -> str:
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {table}
  USING (app_is_platform() OR university_id = app_current_university())
  WITH CHECK (app_is_platform() OR university_id = app_current_university());
"""


def upgrade() -> None:
    op.execute(HELPERS)

    for table in TENANT_TABLES:
        op.execute(_tenant_policy(table))

    # universities: tenant faqat o‘zini ko‘radi va tahrirlaydi; yaratish — platforma.
    op.execute("""
ALTER TABLE universities ENABLE ROW LEVEL SECURITY;
CREATE POLICY platform_all ON universities USING (app_is_platform()) WITH CHECK (app_is_platform());
CREATE POLICY tenant_self_read ON universities FOR SELECT USING (id = app_current_university());
CREATE POLICY tenant_self_update ON universities FOR UPDATE
  USING (id = app_current_university()) WITH CHECK (id = app_current_university());
""")
    # subscriptions: tenant faqat o‘qiydi.
    op.execute("""
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY platform_all ON subscriptions USING (app_is_platform()) WITH CHECK (app_is_platform());
CREATE POLICY tenant_read ON subscriptions FOR SELECT USING (university_id = app_current_university());
""")
    # roles: tizim rollari (university_id IS NULL) hammaga ko‘rinadi, lekin faqat platforma o‘zgartiradi.
    op.execute("""
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON roles
  USING (app_is_platform() OR university_id = app_current_university())
  WITH CHECK (app_is_platform() OR university_id = app_current_university());
CREATE POLICY system_roles_read ON roles FOR SELECT USING (university_id IS NULL);
""")
    # role_permissions: rol ko‘rinsa ko‘rinadi; yozish faqat o‘z tenant rollariga.
    op.execute("""
ALTER TABLE role_permissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY visible_role_read ON role_permissions FOR SELECT
  USING (EXISTS (SELECT 1 FROM roles r WHERE r.id = role_id));
CREATE POLICY own_role_write ON role_permissions
  USING (EXISTS (SELECT 1 FROM roles r WHERE r.id = role_id
                 AND (app_is_platform() OR r.university_id = app_current_university())))
  WITH CHECK (EXISTS (SELECT 1 FROM roles r WHERE r.id = role_id
                      AND (app_is_platform() OR r.university_id = app_current_university())));
""")
    # audit_logs: o‘qish — o‘z tenanti; yozish — o‘z tenanti yoki tenantsiz (masalan, noma’lum email bilan kirish).
    op.execute("""
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_read ON audit_logs FOR SELECT
  USING (app_is_platform() OR university_id = app_current_university());
CREATE POLICY tenant_insert ON audit_logs FOR INSERT
  WITH CHECK (app_is_platform() OR university_id IS NULL OR university_id = app_current_university());
""")

    op.execute(YEAR_LOCK)
    op.execute("""
CREATE TRIGGER academic_year_guard BEFORE UPDATE OR DELETE ON academic_years
  FOR EACH ROW EXECUTE FUNCTION trg_academic_year_guard();
""")
    for table in YEAR_SCOPED_TABLES:
        op.execute(f"""
CREATE TRIGGER year_lock BEFORE INSERT OR UPDATE OR DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION trg_year_lock();
""")

    # Ilova roli huquqlari. Rol docker/postgres/init/01-roles.sql da yaratiladi.
    op.execute(f"""
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN
    CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{APP_ROLE}' NOSUPERUSER NOBYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO {APP_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {APP_ROLE};
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {APP_ROLE};
REVOKE ALL ON alembic_version FROM {APP_ROLE};
REVOKE UPDATE, DELETE ON audit_logs FROM {APP_ROLE};
REVOKE INSERT, UPDATE, DELETE ON permissions FROM {APP_ROLE};
""")

    permissions = sa.table("permissions", sa.column("id", sa.Uuid), sa.column("code", sa.String),
                           sa.column("module", sa.String), sa.column("description", sa.String))
    op.bulk_insert(permissions, [{"id": uuid7(), "code": code, "module": module, "description": desc}
                                 for code, (module, desc) in PERMISSIONS.items()])


def downgrade() -> None:
    op.execute("DELETE FROM permissions")
    for table in YEAR_SCOPED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS year_lock ON {table}")
    op.execute("DROP TRIGGER IF EXISTS academic_year_guard ON academic_years")
    op.execute("DROP FUNCTION IF EXISTS trg_year_lock(); DROP FUNCTION IF EXISTS trg_academic_year_guard();")
    for table in [*TENANT_TABLES, "universities", "subscriptions", "roles", "role_permissions", "audit_logs"]:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        rows = ["tenant_isolation", "platform_all", "tenant_self_read", "tenant_self_update", "tenant_read",
                "system_roles_read", "visible_role_read", "own_role_write", "tenant_insert"]
        for policy in rows:
            op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS app_current_university(); DROP FUNCTION IF EXISTS app_is_platform();"
               " DROP FUNCTION IF EXISTS app_override_reason();")
