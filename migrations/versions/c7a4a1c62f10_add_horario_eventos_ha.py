"""add horario eventos (HA)

Revision ID: c7a4a1c62f10
Revises: 9c2f1a4b7d1e
Create Date: 2026-02-10 16:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7a4a1c62f10"
down_revision = "9c2f1a4b7d1e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "horario_evento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("professor_id", sa.Integer(), nullable=False),
        sa.Column("dia_semana", sa.Integer(), nullable=False),  # 0=Seg..6=Dom
        sa.Column("hora", sa.String(length=5), nullable=False),  # HH:MM
        sa.Column("periodo", sa.String(length=16), nullable=False),  # Manhã|Tarde|Noite
        sa.Column("titulo", sa.String(length=120), nullable=False),  # ex: HA
        sa.Column("subtitulo", sa.String(length=255), nullable=True),  # ex: Hora Atividade
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["professor_id"], ["professor.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "professor_id",
            "dia_semana",
            "hora",
            "periodo",
            name="uq_horario_evento_slot",
        ),
    )
    with op.batch_alter_table("horario_evento", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_horario_evento_professor_id"), ["professor_id"], unique=False)


def downgrade():
    with op.batch_alter_table("horario_evento", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_horario_evento_professor_id"))
    op.drop_table("horario_evento")

