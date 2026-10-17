"""2-bosqich jadvallari uchun RLS, o‘quv yili va o‘quv reja qulflari, ilova roli huquqlari.

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

APP_ROLE = "uniload_app"

TENANT_TABLES = [
    "faculties", "departments", "education_programs", "lesson_types", "subjects", "curricula",
    "curriculum_subjects", "curriculum_subject_hours", "student_groups", "streams", "stream_groups",
    "teachers", "position_norms", "teacher_employment",
]
YEAR_SCOPED_TABLES = ["student_groups", "streams", "stream_groups", "position_norms", "teacher_employment"]

CURRICULUM_LOCK = """
-- Tasdiqlangan/arxivlangan o‘quv reja tarkibi o‘zgarmaydi (o‘zgarish — yangi versiya).
CREATE OR REPLACE FUNCTION trg_curriculum_content_lock() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
  v_curriculum uuid;
  v_status text;
BEGIN
  IF app_override_reason() IS NOT NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;
  IF TG_TABLE_NAME = 'curriculum_subjects' THEN
    v_curriculum := COALESCE(NEW.curriculum_id, OLD.curriculum_id);
  ELSE
    SELECT cs.curriculum_id INTO v_curriculum FROM curriculum_subjects cs
     WHERE cs.id = COALESCE(NEW.curriculum_subject_id, OLD.curriculum_subject_id);
  END IF;
  SELECT status INTO v_status FROM curricula WHERE id = v_curriculum;
  IF v_status IN ('approved', 'archived') THEN
    RAISE EXCEPTION 'O‘quv reja "%" holatida — tarkibini o‘zgartirib bo‘lmaydi', v_status USING ERRCODE = 'UL002';
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;

-- curricula jadvalining o‘zi: tasdiqlangandan keyin faqat arxivlash mumkin.
CREATE OR REPLACE FUNCTION trg_curriculum_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF app_override_reason() IS NOT NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;
  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'draft' THEN
      RAISE EXCEPTION 'Faqat qoralama o‘quv rejani o‘chirish mumkin' USING ERRCODE = 'UL002';
    END IF;
    RETURN OLD;
  END IF;
  IF OLD.status IN ('approved', 'archived') THEN
    IF (NEW.education_program_id, NEW.education_form, NEW.admission_year, NEW.version, NEW.approval_doc)
       IS DISTINCT FROM (OLD.education_program_id, OLD.education_form, OLD.admission_year, OLD.version, OLD.approval_doc)
       OR (OLD.status = 'archived' AND NEW.status <> 'archived')
       OR (OLD.status = 'approved' AND NEW.status NOT IN ('approved', 'archived')) THEN
      RAISE EXCEPTION 'Tasdiqlangan o‘quv rejani o‘zgartirib bo‘lmaydi — yangi versiya yarating' USING ERRCODE = 'UL002';
    END IF;
  END IF;
  RETURN NEW;
END $$;
"""


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {table}
  USING (app_is_platform() OR university_id = app_current_university())
  WITH CHECK (app_is_platform() OR university_id = app_current_university());
""")
    for table in YEAR_SCOPED_TABLES:
        op.execute(f"""
CREATE TRIGGER year_lock BEFORE INSERT OR UPDATE OR DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION trg_year_lock();
""")
    op.execute(CURRICULUM_LOCK)
    op.execute("""
CREATE TRIGGER curriculum_guard BEFORE UPDATE OR DELETE ON curricula
  FOR EACH ROW EXECUTE FUNCTION trg_curriculum_guard();
CREATE TRIGGER curriculum_content_lock BEFORE INSERT OR UPDATE OR DELETE ON curriculum_subjects
  FOR EACH ROW EXECUTE FUNCTION trg_curriculum_content_lock();
CREATE TRIGGER curriculum_content_lock BEFORE INSERT OR UPDATE OR DELETE ON curriculum_subject_hours
  FOR EACH ROW EXECUTE FUNCTION trg_curriculum_content_lock();
""")
    tables = ", ".join(TENANT_TABLES)
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tables} TO {APP_ROLE};")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS curriculum_guard ON curricula")
    for table in ("curriculum_subjects", "curriculum_subject_hours"):
        op.execute(f"DROP TRIGGER IF EXISTS curriculum_content_lock ON {table}")
    op.execute("DROP FUNCTION IF EXISTS trg_curriculum_content_lock(); DROP FUNCTION IF EXISTS trg_curriculum_guard();")
    for table in YEAR_SCOPED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS year_lock ON {table}")
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}; ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
