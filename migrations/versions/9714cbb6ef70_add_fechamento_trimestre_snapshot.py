"""add fechamento trimestre snapshot

Revision ID: 9714cbb6ef70
Revises: 6a9a2d0a3f21
Create Date: 2026-02-11

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9714cbb6ef70"
down_revision = "6a9a2d0a3f21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fechamento_trimestre_aluno",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turma_id", sa.Integer(), nullable=False),
        sa.Column("estudante_id", sa.Integer(), nullable=False),
        sa.Column("ano_letivo", sa.Integer(), nullable=False),
        sa.Column("trimestre", sa.Integer(), nullable=False),
        sa.Column("media_final", sa.Float(), nullable=True),
        sa.Column("total_pontos", sa.Float(), nullable=True),
        sa.Column("avaliadas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_previstas", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["estudante_id"], ["estudante.id"]),
        sa.ForeignKeyConstraint(["turma_id"], ["turma.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "turma_id",
            "estudante_id",
            "ano_letivo",
            "trimestre",
            name="uq_fechamento_turma_estudante_ano_tri",
        ),
    )
    with op.batch_alter_table("fechamento_trimestre_aluno", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_fechamento_trimestre_aluno_estudante_id"), ["estudante_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_fechamento_trimestre_aluno_turma_id"), ["turma_id"], unique=False)


def downgrade():
    with op.batch_alter_table("fechamento_trimestre_aluno", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_fechamento_trimestre_aluno_turma_id"))
        batch_op.drop_index(batch_op.f("ix_fechamento_trimestre_aluno_estudante_id"))
    op.drop_table("fechamento_trimestre_aluno")

