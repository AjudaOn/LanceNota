"""add professor is_admin and admin/user updates

Revision ID: 0b1e6c6dd2a7
Revises: c7a4a1c62f10
Create Date: 2026-02-10 16:30:00.000000

"""

from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


# revision identifiers, used by Alembic.
revision = "0b1e6c6dd2a7"
down_revision = "c7a4a1c62f10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("professor", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_admin", sa.Boolean(), nullable=True))

    bind = op.get_bind()

    professor = sa.table(
        "professor",
        sa.column("id", sa.Integer()),
        sa.column("nome", sa.String()),
        sa.column("email", sa.String()),
        sa.column("senha_hash", sa.String()),
        sa.column("is_admin", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
    )

    bind.execute(professor.update().where(professor.c.is_admin.is_(None)).values(is_admin=False))

    # Update Aurea email (old demo email -> new email), if present
    aurea_old = "demo@example.com"
    aurea_new = "aureafazarte@gmail.com"
    existing_new = bind.execute(sa.select(professor.c.id).where(professor.c.email == aurea_new)).first()
    if existing_new is None:
        bind.execute(professor.update().where(professor.c.email == aurea_old).values(email=aurea_new))

    # Ensure Admin user exists
    admin_email = "edirfonseca@outlook.com"
    admin_exists = bind.execute(sa.select(professor.c.id).where(professor.c.email == admin_email)).first()
    if admin_exists is None:
        bind.execute(
            professor.insert().values(
                nome="Edir Fonseca",
                email=admin_email,
                senha_hash=generate_password_hash("12345"),
                is_admin=True,
                created_at=datetime.utcnow(),
            )
        )
    else:
        bind.execute(professor.update().where(professor.c.email == admin_email).values(is_admin=True))

    with op.batch_alter_table("professor", schema=None) as batch_op:
        batch_op.alter_column("is_admin", existing_type=sa.Boolean(), nullable=False)


def downgrade():
    bind = op.get_bind()

    professor = sa.table(
        "professor",
        sa.column("id", sa.Integer()),
        sa.column("email", sa.String()),
        sa.column("is_admin", sa.Boolean()),
    )

    # Best-effort cleanup
    bind.execute(professor.delete().where(professor.c.email == "edirfonseca@outlook.com"))
    bind.execute(professor.update().where(professor.c.email == "aureafazarte@gmail.com").values(email="demo@example.com"))

    with op.batch_alter_table("professor", schema=None) as batch_op:
        batch_op.drop_column("is_admin")

