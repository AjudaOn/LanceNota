"""add locked snapshot origin

Revision ID: 2c3b5e6f7a8b
Revises: 1d8d7fb2fd2c
Create Date: 2026-02-11

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2c3b5e6f7a8b"
down_revision = "1d8d7fb2fd2c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("fechamento_trimestre_aluno", schema=None) as batch_op:
        batch_op.add_column(sa.Column("origem_turma_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.create_index(batch_op.f("ix_fechamento_trimestre_aluno_origem_turma_id"), ["origem_turma_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_fechamento_trimestre_aluno_origem_turma_id",
            "turma",
            ["origem_turma_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("fechamento_trimestre_aluno", schema=None) as batch_op:
        batch_op.drop_constraint("fk_fechamento_trimestre_aluno_origem_turma_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_fechamento_trimestre_aluno_origem_turma_id"))
        batch_op.drop_column("locked")
        batch_op.drop_column("origem_turma_id")

