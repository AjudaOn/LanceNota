"""add fechamento trimestre flag

Revision ID: 7f3d1d0bb8d8
Revises: 9714cbb6ef70
Create Date: 2026-02-11

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7f3d1d0bb8d8"
down_revision = "9714cbb6ef70"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fechamento_trimestre_turma",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turma_id", sa.Integer(), nullable=False),
        sa.Column("ano_letivo", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="aberto"),
        sa.Column("fechado_em", sa.DateTime(), nullable=True),
        sa.Column("fechado_por_professor_id", sa.Integer(), nullable=True),
        sa.Column("reaberto_em", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fechado_por_professor_id"], ["professor.id"]),
        sa.ForeignKeyConstraint(["turma_id"], ["turma.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turma_id", "ano_letivo", "trimestre", name="uq_fechamento_turma_ano_tri"),
    )
    with op.batch_alter_table("fechamento_trimestre_turma", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fechamento_trimestre_turma_turma_id"), ["turma_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_fechamento_trimestre_turma_fechado_por_professor_id"),
            ["fechado_por_professor_id"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("fechamento_trimestre_turma", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fechamento_trimestre_turma_fechado_por_professor_id"))
        batch_op.drop_index(batch_op.f("ix_fechamento_trimestre_turma_turma_id"))
    op.drop_table("fechamento_trimestre_turma")

