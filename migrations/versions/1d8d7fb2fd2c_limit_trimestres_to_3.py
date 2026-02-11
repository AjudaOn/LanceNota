"""limit trimestres to 3

Revision ID: 1d8d7fb2fd2c
Revises: 7f3d1d0bb8d8
Create Date: 2026-02-11

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1d8d7fb2fd2c"
down_revision = "7f3d1d0bb8d8"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    turma = sa.table(
        "turma",
        sa.column("id", sa.Integer()),
        sa.column("trimestre_atual", sa.Integer()),
    )
    atividade = sa.table(
        "atividade",
        sa.column("id", sa.Integer()),
        sa.column("trimestre", sa.Integer()),
    )
    fechamento_turma = sa.table(
        "fechamento_trimestre_turma",
        sa.column("id", sa.Integer()),
        sa.column("turma_id", sa.Integer()),
        sa.column("ano_letivo", sa.Integer()),
        sa.column("trimestre", sa.Integer()),
    )
    fechamento_aluno = sa.table(
        "fechamento_trimestre_aluno",
        sa.column("id", sa.Integer()),
        sa.column("turma_id", sa.Integer()),
        sa.column("estudante_id", sa.Integer()),
        sa.column("ano_letivo", sa.Integer()),
        sa.column("trimestre", sa.Integer()),
    )

    bind.execute(turma.update().where(turma.c.trimestre_atual > 3).values(trimestre_atual=3))
    bind.execute(atividade.update().where(atividade.c.trimestre > 3).values(trimestre=3))

    # If there are any trimester=4 closure rows, prefer keeping trimester=3 row (delete trimester=4).
    for table in (fechamento_turma, fechamento_aluno):
        rows = bind.execute(sa.select(table.c.id).where(table.c.trimestre > 3)).all()
        if rows:
            ids = [r[0] for r in rows]
            bind.execute(table.delete().where(table.c.id.in_(ids)))


def downgrade():
    # No-op: cannot restore deleted/merged trimester=4 data.
    pass

