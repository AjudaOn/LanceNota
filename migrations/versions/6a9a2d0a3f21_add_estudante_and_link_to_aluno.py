"""add estudante and link to aluno

Revision ID: 6a9a2d0a3f21
Revises: 5f0e3b2a1c9d
Create Date: 2026-02-11

"""

from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6a9a2d0a3f21"
down_revision = "5f0e3b2a1c9d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "estudante",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome_completo", sa.String(length=255), nullable=False),
        sa.Column("matricula", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("estudante", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_estudante_matricula"), ["matricula"], unique=True)

    with op.batch_alter_table("aluno", schema=None) as batch_op:
        batch_op.add_column(sa.Column("estudante_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_aluno_estudante_id"), ["estudante_id"], unique=False)
        batch_op.create_foreign_key("fk_aluno_estudante_id", "estudante", ["estudante_id"], ["id"])

    bind = op.get_bind()

    meta = sa.MetaData()
    estudante = sa.Table(
        "estudante",
        meta,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome_completo", sa.String(length=255), nullable=False),
        sa.Column("matricula", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    aluno = sa.Table(
        "aluno",
        meta,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome_completo", sa.String(length=255), nullable=False),
        sa.Column("matricula", sa.String(length=64), nullable=True),
        sa.Column("estudante_id", sa.Integer(), nullable=True),
    )

    existing = bind.execute(sa.select(aluno.c.id, aluno.c.nome_completo, aluno.c.matricula, aluno.c.estudante_id)).all()
    for aluno_id, nome_completo, matricula, estudante_id in existing:
        if estudante_id is not None:
            continue
        res = bind.execute(
            estudante.insert().values(
                nome_completo=nome_completo,
                matricula=(matricula.strip() if isinstance(matricula, str) and matricula.strip() else None),
                created_at=datetime.utcnow(),
            )
        )
        new_id = res.inserted_primary_key[0]
        bind.execute(aluno.update().where(aluno.c.id == aluno_id).values(estudante_id=new_id))


def downgrade():
    with op.batch_alter_table("aluno", schema=None) as batch_op:
        batch_op.drop_constraint("fk_aluno_estudante_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_aluno_estudante_id"))
        batch_op.drop_column("estudante_id")

    with op.batch_alter_table("estudante", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_estudante_matricula"))
    op.drop_table("estudante")

