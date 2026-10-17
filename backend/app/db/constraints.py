"""Tenant va o‘quv yili yaxlitligini DB darajasida ta’minlovchi kompozit FK yordamchilari.

`(university_id, x_id) → x(university_id, id)` ko‘rinishidagi FK bir universitet yozuvini
boshqa universitet yozuviga bog‘lashni imkonsiz qiladi (RLS’dan mustaqil ravishda).
"""

from sqlalchemy import ForeignKeyConstraint, UniqueConstraint


def tenant_unique() -> UniqueConstraint:
    """Kompozit FK nishoni bo‘lishi uchun `(university_id, id)` noyobligi."""
    return UniqueConstraint("university_id", "id")


def tenant_fk(column: str, table: str, ondelete: str = "RESTRICT") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["university_id", column], [f"{table}.university_id", f"{table}.id"],
                                ondelete=ondelete)


def year_fk(ondelete: str = "CASCADE") -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["university_id", "academic_year_id"],
                                ["academic_years.university_id", "academic_years.id"], ondelete=ondelete)


def same_year_fk(column: str, table: str, ondelete: str = "CASCADE") -> ForeignKeyConstraint:
    """`(academic_year_id, x_id) → x(academic_year_id, id)` — bog‘langan yozuv shu yilga tegishli."""
    return ForeignKeyConstraint(["academic_year_id", column], [f"{table}.academic_year_id", f"{table}.id"],
                                ondelete=ondelete)
