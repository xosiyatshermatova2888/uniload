"""Ma’lumotnomalar: tuzilma, yo‘nalishlar, fanlar, o‘quv rejalari, guruhlar, oqimlar, o‘qituvchilar

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17 23:29:24.845287
"""
from alembic import op
import sqlalchemy as sa


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Oqimlar kompozit FK’si uchun — jadvallardan oldin bo‘lishi shart.
    op.create_unique_constraint(op.f('uq_semesters_academic_year_id_id'), 'semesters', ['academic_year_id', 'id'])
    op.create_table('faculties',
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_faculties_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_faculties')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_faculties_university_id_id'))
    )
    op.create_index(op.f('ix_faculties_university_id'), 'faculties', ['university_id'], unique=False)
    op.create_index('uq_faculties_code', 'faculties', ['university_id', sa.literal_column('lower(code)')], unique=True)
    op.create_table('lesson_types',
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('is_auditorium', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('counts_in_workload', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('is_system', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('sort_order', sa.SmallInteger(), server_default='100', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("code ~ '^[a-z0-9_]{2,32}$'", name=op.f('ck_lesson_types_code_format')),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_lesson_types_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lesson_types')),
    sa.UniqueConstraint('university_id', 'code', name=op.f('uq_lesson_types_university_id_code')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_lesson_types_university_id_id'))
    )
    op.create_index(op.f('ix_lesson_types_university_id'), 'lesson_types', ['university_id'], unique=False)
    op.create_table('teachers',
    sa.Column('last_name', sa.String(length=64), nullable=False),
    sa.Column('first_name', sa.String(length=64), nullable=False),
    sa.Column('middle_name', sa.String(length=64), nullable=True),
    sa.Column('employee_no', sa.String(length=32), nullable=False),
    sa.Column('academic_degree', sa.String(length=16), server_default='none', nullable=False),
    sa.Column('academic_title', sa.String(length=24), server_default='none', nullable=False),
    sa.Column('email', sa.String(length=254), nullable=True),
    sa.Column('phone', sa.String(length=32), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("academic_degree IN ('none', 'phd', 'dsc')", name=op.f('ck_teachers_degree')),
    sa.CheckConstraint("academic_title IN ('none', 'docent', 'professor', 'senior_researcher')", name=op.f('ck_teachers_title')),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_teachers_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_teachers')),
    sa.UniqueConstraint('university_id', 'employee_no', name=op.f('uq_teachers_university_id_employee_no')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_teachers_university_id_id'))
    )
    op.create_index('ix_teachers_name', 'teachers', ['university_id', 'last_name', 'first_name'], unique=False)
    op.create_index(op.f('ix_teachers_university_id'), 'teachers', ['university_id'], unique=False)
    op.create_table('position_norms',
    sa.Column('academic_year_id', sa.UUID(), nullable=False),
    sa.Column('position_code', sa.String(length=32), nullable=False),
    sa.Column('norm_hours_per_rate', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('max_overload_pct', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('source_document', sa.Text(), nullable=True),
    sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("position_code IN ('assistant', 'senior_teacher', 'docent', 'professor', 'department_head')", name=op.f('ck_position_norms_position')),
    sa.CheckConstraint('max_overload_pct IS NULL OR max_overload_pct BETWEEN 0 AND 100', name=op.f('ck_position_norms_overload')),
    sa.CheckConstraint('norm_hours_per_rate IS NULL OR norm_hours_per_rate > 0', name=op.f('ck_position_norms_norm')),
    sa.ForeignKeyConstraint(['university_id', 'academic_year_id'], ['academic_years.university_id', 'academic_years.id'], name=op.f('fk_position_norms_university_id_academic_year_id_academic_years'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_position_norms_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_position_norms')),
    sa.UniqueConstraint('academic_year_id', 'position_code', name=op.f('uq_position_norms_academic_year_id_position_code'))
    )
    op.create_index(op.f('ix_position_norms_academic_year_id'), 'position_norms', ['academic_year_id'], unique=False)
    op.create_index(op.f('ix_position_norms_university_id'), 'position_norms', ['university_id'], unique=False)
    op.create_table('departments',
    sa.Column('faculty_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('head_user_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('merged_into_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint('merged_into_id IS NULL OR merged_into_id <> id', name=op.f('ck_departments_not_self_merged')),
    sa.ForeignKeyConstraint(['head_user_id'], ['users.id'], name=op.f('fk_departments_head_user_id_users'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['merged_into_id'], ['departments.id'], name=op.f('fk_departments_merged_into_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id', 'faculty_id'], ['faculties.university_id', 'faculties.id'], name=op.f('fk_departments_university_id_faculty_id_faculties'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_departments_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_departments_university_id_id'))
    )
    op.create_index(op.f('ix_departments_faculty_id'), 'departments', ['faculty_id'], unique=False)
    op.create_index(op.f('ix_departments_university_id'), 'departments', ['university_id'], unique=False)
    op.create_index('uq_departments_code', 'departments', ['university_id', sa.literal_column('lower(code)')], unique=True)
    op.create_table('education_programs',
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('degree', sa.String(length=16), nullable=False),
    sa.Column('duration_years', sa.SmallInteger(), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("degree IN ('bachelor', 'master')", name=op.f('ck_education_programs_degree')),
    sa.CheckConstraint('duration_years BETWEEN 1 AND 6', name=op.f('ck_education_programs_duration')),
    sa.ForeignKeyConstraint(['university_id', 'department_id'], ['departments.university_id', 'departments.id'], name=op.f('fk_education_programs_university_id_department_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_education_programs_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_education_programs')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_education_programs_university_id_id'))
    )
    op.create_index(op.f('ix_education_programs_department_id'), 'education_programs', ['department_id'], unique=False)
    op.create_index(op.f('ix_education_programs_university_id'), 'education_programs', ['university_id'], unique=False)
    op.create_index('uq_education_programs_code', 'education_programs', ['university_id', 'code', 'degree'], unique=True)
    op.create_table('subjects',
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('name_uz', sa.String(length=255), nullable=False),
    sa.Column('name_ru', sa.String(length=255), nullable=True),
    sa.Column('name_en', sa.String(length=255), nullable=True),
    sa.Column('default_department_id', sa.UUID(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['university_id', 'default_department_id'], ['departments.university_id', 'departments.id'], name=op.f('fk_subjects_university_id_default_department_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_subjects_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subjects')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_subjects_university_id_id'))
    )
    op.create_index(op.f('ix_subjects_default_department_id'), 'subjects', ['default_department_id'], unique=False)
    op.create_index(op.f('ix_subjects_university_id'), 'subjects', ['university_id'], unique=False)
    op.create_index('uq_subjects_code', 'subjects', ['university_id', sa.literal_column('lower(code)')], unique=True)
    op.create_table('teacher_employment',
    sa.Column('academic_year_id', sa.UUID(), nullable=False),
    sa.Column('teacher_id', sa.UUID(), nullable=False),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('position_code', sa.String(length=32), nullable=False),
    sa.Column('employment_type', sa.String(length=24), server_default='main', nullable=False),
    sa.Column('rate', sa.Numeric(precision=4, scale=2), nullable=False),
    sa.Column('norm_hours', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('starts_on', sa.Date(), nullable=True),
    sa.Column('ends_on', sa.Date(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("employment_type IN ('main', 'internal_part_time', 'external_part_time', 'hourly')", name=op.f('ck_teacher_employment_employment_type')),
    sa.CheckConstraint("position_code IN ('assistant', 'senior_teacher', 'docent', 'professor', 'department_head')", name=op.f('ck_teacher_employment_position')),
    sa.CheckConstraint('ends_on IS NULL OR starts_on IS NULL OR ends_on > starts_on', name=op.f('ck_teacher_employment_dates')),
    sa.CheckConstraint('rate > 0 AND rate <= 2', name=op.f('ck_teacher_employment_rate')),
    sa.ForeignKeyConstraint(['university_id', 'academic_year_id'], ['academic_years.university_id', 'academic_years.id'], name=op.f('fk_teacher_employment_university_id_academic_year_id_academic_years'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'department_id'], ['departments.university_id', 'departments.id'], name=op.f('fk_teacher_employment_university_id_department_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id', 'teacher_id'], ['teachers.university_id', 'teachers.id'], name=op.f('fk_teacher_employment_university_id_teacher_id_teachers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_teacher_employment_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_teacher_employment')),
    sa.UniqueConstraint('academic_year_id', 'teacher_id', 'department_id', 'employment_type', name=op.f('uq_teacher_employment_academic_year_id_teacher_id_department_id_employment_type'))
    )
    op.create_index(op.f('ix_teacher_employment_academic_year_id'), 'teacher_employment', ['academic_year_id'], unique=False)
    op.create_index('ix_teacher_employment_department', 'teacher_employment', ['academic_year_id', 'department_id'], unique=False)
    op.create_index(op.f('ix_teacher_employment_teacher_id'), 'teacher_employment', ['teacher_id'], unique=False)
    op.create_index(op.f('ix_teacher_employment_university_id'), 'teacher_employment', ['university_id'], unique=False)
    op.create_table('curricula',
    sa.Column('education_program_id', sa.UUID(), nullable=False),
    sa.Column('education_form', sa.String(length=16), nullable=False),
    sa.Column('admission_year', sa.SmallInteger(), nullable=False),
    sa.Column('version', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('status', sa.String(length=16), server_default='draft', nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('approval_doc', sa.Text(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by', sa.UUID(), nullable=True),
    sa.Column('based_on_id', sa.UUID(), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("education_form IN ('full_time', 'part_time', 'evening', 'distance')", name=op.f('ck_curricula_education_form')),
    sa.CheckConstraint("status IN ('draft', 'approved', 'archived')", name=op.f('ck_curricula_status')),
    sa.CheckConstraint('admission_year BETWEEN 2000 AND 2100', name=op.f('ck_curricula_admission_year')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_curricula_version')),
    sa.ForeignKeyConstraint(['university_id', 'education_program_id'], ['education_programs.university_id', 'education_programs.id'], name=op.f('fk_curricula_university_id_education_program_id_education_programs'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_curricula_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_curricula')),
    sa.UniqueConstraint('university_id', 'education_program_id', 'education_form', 'admission_year', 'version', name=op.f('uq_curricula_university_id_education_program_id_education_form_admission_year_version')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_curricula_university_id_id'))
    )
    op.create_index(op.f('ix_curricula_education_program_id'), 'curricula', ['education_program_id'], unique=False)
    op.create_index(op.f('ix_curricula_university_id'), 'curricula', ['university_id'], unique=False)
    op.create_table('streams',
    sa.Column('academic_year_id', sa.UUID(), nullable=False),
    sa.Column('semester_id', sa.UUID(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('lesson_type_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['academic_year_id', 'semester_id'], ['semesters.academic_year_id', 'semesters.id'], name=op.f('fk_streams_academic_year_id_semester_id_semesters'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'academic_year_id'], ['academic_years.university_id', 'academic_years.id'], name=op.f('fk_streams_university_id_academic_year_id_academic_years'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'lesson_type_id'], ['lesson_types.university_id', 'lesson_types.id'], name=op.f('fk_streams_university_id_lesson_type_id_lesson_types'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id', 'subject_id'], ['subjects.university_id', 'subjects.id'], name=op.f('fk_streams_university_id_subject_id_subjects'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_streams_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_streams')),
    sa.UniqueConstraint('academic_year_id', 'id', name=op.f('uq_streams_academic_year_id_id'))
    )
    op.create_index(op.f('ix_streams_academic_year_id'), 'streams', ['academic_year_id'], unique=False)
    op.create_index('ix_streams_subject', 'streams', ['academic_year_id', 'subject_id'], unique=False)
    op.create_index(op.f('ix_streams_university_id'), 'streams', ['university_id'], unique=False)
    op.create_table('curriculum_subjects',
    sa.Column('curriculum_id', sa.UUID(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('semester_no', sa.SmallInteger(), nullable=False),
    sa.Column('credits', sa.Numeric(precision=5, scale=1), nullable=True),
    sa.Column('department_id', sa.UUID(), nullable=False),
    sa.Column('control_type', sa.String(length=16), server_default='exam', nullable=False),
    sa.Column('is_elective', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('elective_group', sa.String(length=32), nullable=True),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("control_type IN ('exam', 'credit_test', 'none')", name=op.f('ck_curriculum_subjects_control_type')),
    sa.CheckConstraint('credits IS NULL OR credits >= 0', name=op.f('ck_curriculum_subjects_credits')),
    sa.CheckConstraint('semester_no BETWEEN 1 AND 12', name=op.f('ck_curriculum_subjects_semester_no')),
    sa.ForeignKeyConstraint(['university_id', 'curriculum_id'], ['curricula.university_id', 'curricula.id'], name=op.f('fk_curriculum_subjects_university_id_curriculum_id_curricula'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'department_id'], ['departments.university_id', 'departments.id'], name=op.f('fk_curriculum_subjects_university_id_department_id_departments'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id', 'subject_id'], ['subjects.university_id', 'subjects.id'], name=op.f('fk_curriculum_subjects_university_id_subject_id_subjects'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_curriculum_subjects_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_curriculum_subjects')),
    sa.UniqueConstraint('curriculum_id', 'subject_id', 'semester_no', name=op.f('uq_curriculum_subjects_curriculum_id_subject_id_semester_no')),
    sa.UniqueConstraint('university_id', 'id', name=op.f('uq_curriculum_subjects_university_id_id'))
    )
    op.create_index(op.f('ix_curriculum_subjects_curriculum_id'), 'curriculum_subjects', ['curriculum_id'], unique=False)
    op.create_index(op.f('ix_curriculum_subjects_department_id'), 'curriculum_subjects', ['department_id'], unique=False)
    op.create_index(op.f('ix_curriculum_subjects_subject_id'), 'curriculum_subjects', ['subject_id'], unique=False)
    op.create_index(op.f('ix_curriculum_subjects_university_id'), 'curriculum_subjects', ['university_id'], unique=False)
    op.create_table('student_groups',
    sa.Column('academic_year_id', sa.UUID(), nullable=False),
    sa.Column('curriculum_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('course', sa.SmallInteger(), nullable=False),
    sa.Column('language', sa.String(length=3), server_default='uz', nullable=False),
    sa.Column('student_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('budget_count', sa.Integer(), nullable=True),
    sa.Column('contract_count', sa.Integer(), nullable=True),
    sa.Column('subgroup_count', sa.SmallInteger(), server_default='1', nullable=False),
    sa.Column('source_group_id', sa.UUID(), nullable=True),
    sa.Column('needs_review', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint("language IN ('uz', 'ru', 'en', 'kk', 'tj', 'tk', 'kaa')", name=op.f('ck_student_groups_language')),
    sa.CheckConstraint('budget_count IS NULL OR budget_count >= 0', name=op.f('ck_student_groups_budget_count')),
    sa.CheckConstraint('budget_count IS NULL OR contract_count IS NULL OR budget_count + contract_count = student_count', name=op.f('ck_student_groups_contingent_sum')),
    sa.CheckConstraint('contract_count IS NULL OR contract_count >= 0', name=op.f('ck_student_groups_contract_count')),
    sa.CheckConstraint('course BETWEEN 1 AND 6', name=op.f('ck_student_groups_course')),
    sa.CheckConstraint('student_count >= 0', name=op.f('ck_student_groups_student_count')),
    sa.CheckConstraint('subgroup_count BETWEEN 1 AND 10', name=op.f('ck_student_groups_subgroup_count')),
    sa.ForeignKeyConstraint(['source_group_id'], ['student_groups.id'], name=op.f('fk_student_groups_source_group_id_student_groups'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['university_id', 'academic_year_id'], ['academic_years.university_id', 'academic_years.id'], name=op.f('fk_student_groups_university_id_academic_year_id_academic_years'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'curriculum_id'], ['curricula.university_id', 'curricula.id'], name=op.f('fk_student_groups_university_id_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_student_groups_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_groups')),
    sa.UniqueConstraint('academic_year_id', 'id', name=op.f('uq_student_groups_academic_year_id_id'))
    )
    op.create_index(op.f('ix_student_groups_academic_year_id'), 'student_groups', ['academic_year_id'], unique=False)
    op.create_index('ix_student_groups_curriculum_course', 'student_groups', ['academic_year_id', 'curriculum_id', 'course'], unique=False)
    op.create_index(op.f('ix_student_groups_curriculum_id'), 'student_groups', ['curriculum_id'], unique=False)
    op.create_index(op.f('ix_student_groups_university_id'), 'student_groups', ['university_id'], unique=False)
    op.create_index('uq_student_groups_code', 'student_groups', ['academic_year_id', sa.literal_column('lower(code)')], unique=True)
    op.create_table('curriculum_subject_hours',
    sa.Column('curriculum_subject_id', sa.UUID(), nullable=False),
    sa.Column('lesson_type_id', sa.UUID(), nullable=False),
    sa.Column('hours', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_by', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), server_default='1', nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.CheckConstraint('hours >= 0', name=op.f('ck_curriculum_subject_hours_hours')),
    sa.ForeignKeyConstraint(['university_id', 'curriculum_subject_id'], ['curriculum_subjects.university_id', 'curriculum_subjects.id'], name=op.f('fk_curriculum_subject_hours_university_id_curriculum_subject_id_curriculum_subjects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'lesson_type_id'], ['lesson_types.university_id', 'lesson_types.id'], name=op.f('fk_curriculum_subject_hours_university_id_lesson_type_id_lesson_types'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_curriculum_subject_hours_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_curriculum_subject_hours')),
    sa.UniqueConstraint('curriculum_subject_id', 'lesson_type_id', name=op.f('uq_curriculum_subject_hours_curriculum_subject_id_lesson_type_id'))
    )
    op.create_index(op.f('ix_curriculum_subject_hours_curriculum_subject_id'), 'curriculum_subject_hours', ['curriculum_subject_id'], unique=False)
    op.create_index(op.f('ix_curriculum_subject_hours_university_id'), 'curriculum_subject_hours', ['university_id'], unique=False)
    op.create_table('stream_groups',
    sa.Column('academic_year_id', sa.UUID(), nullable=False),
    sa.Column('stream_id', sa.UUID(), nullable=False),
    sa.Column('group_id', sa.UUID(), nullable=False),
    sa.Column('university_id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['academic_year_id', 'group_id'], ['student_groups.academic_year_id', 'student_groups.id'], name=op.f('fk_stream_groups_academic_year_id_group_id_student_groups'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['academic_year_id', 'stream_id'], ['streams.academic_year_id', 'streams.id'], name=op.f('fk_stream_groups_academic_year_id_stream_id_streams'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id', 'academic_year_id'], ['academic_years.university_id', 'academic_years.id'], name=op.f('fk_stream_groups_university_id_academic_year_id_academic_years'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['university_id'], ['universities.id'], name=op.f('fk_stream_groups_university_id_universities'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('stream_id', 'group_id', name=op.f('pk_stream_groups'))
    )
    op.create_index(op.f('ix_stream_groups_group_id'), 'stream_groups', ['group_id'], unique=False)
    op.create_index(op.f('ix_stream_groups_university_id'), 'stream_groups', ['university_id'], unique=False)
    op.create_foreign_key(op.f('fk_users_teacher_id_teachers'), 'users', 'teachers', ['teacher_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(op.f('fk_users_teacher_id_teachers'), 'users', type_='foreignkey')
    op.drop_index(op.f('ix_stream_groups_university_id'), table_name='stream_groups')
    op.drop_index(op.f('ix_stream_groups_group_id'), table_name='stream_groups')
    op.drop_table('stream_groups')
    op.drop_index(op.f('ix_curriculum_subject_hours_university_id'), table_name='curriculum_subject_hours')
    op.drop_index(op.f('ix_curriculum_subject_hours_curriculum_subject_id'), table_name='curriculum_subject_hours')
    op.drop_table('curriculum_subject_hours')
    op.drop_index('uq_student_groups_code', table_name='student_groups')
    op.drop_index(op.f('ix_student_groups_university_id'), table_name='student_groups')
    op.drop_index(op.f('ix_student_groups_curriculum_id'), table_name='student_groups')
    op.drop_index('ix_student_groups_curriculum_course', table_name='student_groups')
    op.drop_index(op.f('ix_student_groups_academic_year_id'), table_name='student_groups')
    op.drop_table('student_groups')
    op.drop_index(op.f('ix_curriculum_subjects_university_id'), table_name='curriculum_subjects')
    op.drop_index(op.f('ix_curriculum_subjects_subject_id'), table_name='curriculum_subjects')
    op.drop_index(op.f('ix_curriculum_subjects_department_id'), table_name='curriculum_subjects')
    op.drop_index(op.f('ix_curriculum_subjects_curriculum_id'), table_name='curriculum_subjects')
    op.drop_table('curriculum_subjects')
    op.drop_index(op.f('ix_streams_university_id'), table_name='streams')
    op.drop_index('ix_streams_subject', table_name='streams')
    op.drop_index(op.f('ix_streams_academic_year_id'), table_name='streams')
    op.drop_table('streams')
    op.drop_index(op.f('ix_curricula_university_id'), table_name='curricula')
    op.drop_index(op.f('ix_curricula_education_program_id'), table_name='curricula')
    op.drop_table('curricula')
    op.drop_index(op.f('ix_teacher_employment_university_id'), table_name='teacher_employment')
    op.drop_index(op.f('ix_teacher_employment_teacher_id'), table_name='teacher_employment')
    op.drop_index('ix_teacher_employment_department', table_name='teacher_employment')
    op.drop_index(op.f('ix_teacher_employment_academic_year_id'), table_name='teacher_employment')
    op.drop_table('teacher_employment')
    op.drop_index('uq_subjects_code', table_name='subjects')
    op.drop_index(op.f('ix_subjects_university_id'), table_name='subjects')
    op.drop_index(op.f('ix_subjects_default_department_id'), table_name='subjects')
    op.drop_table('subjects')
    op.drop_index('uq_education_programs_code', table_name='education_programs')
    op.drop_index(op.f('ix_education_programs_university_id'), table_name='education_programs')
    op.drop_index(op.f('ix_education_programs_department_id'), table_name='education_programs')
    op.drop_table('education_programs')
    op.drop_index('uq_departments_code', table_name='departments')
    op.drop_index(op.f('ix_departments_university_id'), table_name='departments')
    op.drop_index(op.f('ix_departments_faculty_id'), table_name='departments')
    op.drop_table('departments')
    op.drop_index(op.f('ix_position_norms_university_id'), table_name='position_norms')
    op.drop_index(op.f('ix_position_norms_academic_year_id'), table_name='position_norms')
    op.drop_table('position_norms')
    op.drop_index(op.f('ix_teachers_university_id'), table_name='teachers')
    op.drop_index('ix_teachers_name', table_name='teachers')
    op.drop_table('teachers')
    op.drop_index(op.f('ix_lesson_types_university_id'), table_name='lesson_types')
    op.drop_table('lesson_types')
    op.drop_index('uq_faculties_code', table_name='faculties')
    op.drop_index(op.f('ix_faculties_university_id'), table_name='faculties')
    op.drop_table('faculties')
    op.drop_constraint(op.f('uq_semesters_academic_year_id_id'), 'semesters', type_='unique')
    # ### end Alembic commands ###
