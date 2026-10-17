"""Login + parol bilan kirish: `users.username` (majburiy, noyob), `users.email` ixtiyoriy.

Mavjud foydalanuvchilarga login emailning `@` gacha qismidan va ID’ning tasodifiy qismidan beriladi (noyoblik uchun);
administrator uni keyin o‘zgartira oladi.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.execute("""
UPDATE users SET username =
  left(regexp_replace(lower(split_part(email, '@', 1)), '[^a-z0-9._-]', '', 'g'), 50)
  || '.' || right(replace(id::text, '-', ''), 8)
""")
    op.execute("UPDATE users SET username = 'u' || username WHERE username !~ '^[a-z0-9]'")
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint(op.f("uq_users_username"), "users", ["username"])
    op.create_check_constraint(op.f("ck_users_username_format"), "users", "username ~ '^[a-z0-9][a-z0-9._-]{2,63}$'")
    op.drop_constraint(op.f("ck_users_email_lower"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_email_lower"), "users", "email IS NULL OR email = lower(email)")
    op.alter_column("users", "email", existing_type=sa.String(length=254), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE users SET email = username || '@uniload.invalid' WHERE email IS NULL")
    op.alter_column("users", "email", existing_type=sa.String(length=254), nullable=False)
    op.drop_constraint(op.f("ck_users_email_lower"), "users", type_="check")
    op.create_check_constraint(op.f("ck_users_email_lower"), "users", "email = lower(email)")
    op.drop_constraint(op.f("ck_users_username_format"), "users", type_="check")
    op.drop_constraint(op.f("uq_users_username"), "users", type_="unique")
    op.drop_column("users", "username")
