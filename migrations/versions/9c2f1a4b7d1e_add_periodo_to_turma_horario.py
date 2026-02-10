"""add periodo to turma horario

Revision ID: 9c2f1a4b7d1e
Revises: b3bc29eea071
Create Date: 2026-02-10 15:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c2f1a4b7d1e"
down_revision = "b3bc29eea071"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("turma_horario", schema=None) as batch_op:
        batch_op.add_column(sa.Column("periodo", sa.String(length=16), nullable=True))

    # Backfill: copy from turma.periodo when available; fallback to 'Manhã' to avoid NULL.
    op.execute(
        """
        UPDATE turma_horario
        SET periodo = COALESCE(
          (SELECT turma.periodo FROM turma WHERE turma.id = turma_horario.turma_id),
          'Manhã'
        )
        WHERE periodo IS NULL
        """
    )

    with op.batch_alter_table("turma_horario", schema=None) as batch_op:
        batch_op.alter_column("periodo", existing_type=sa.String(length=16), nullable=False)
        batch_op.drop_constraint("uq_turma_horario_dia_hora", type_="unique")
        batch_op.create_unique_constraint(
            "uq_turma_horario_dia_hora_periodo",
            ["turma_id", "dia_semana", "hora", "periodo"],
        )


def downgrade():
    with op.batch_alter_table("turma_horario", schema=None) as batch_op:
        batch_op.drop_constraint("uq_turma_horario_dia_hora_periodo", type_="unique")
        batch_op.create_unique_constraint(
            "uq_turma_horario_dia_hora",
            ["turma_id", "dia_semana", "hora"],
        )
        batch_op.drop_column("periodo")

