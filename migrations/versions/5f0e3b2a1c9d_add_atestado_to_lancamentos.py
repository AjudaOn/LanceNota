"""add atestado to lancamentos

Revision ID: 5f0e3b2a1c9d
Revises: 0b1e6c6dd2a7
Create Date: 2026-02-10 17:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5f0e3b2a1c9d"
down_revision = "0b1e6c6dd2a7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("lancamento_aula_aluno", schema=None) as batch_op:
        batch_op.add_column(sa.Column("atestado", sa.Boolean(), nullable=True))

    op.execute("UPDATE lancamento_aula_aluno SET atestado = 0 WHERE atestado IS NULL")

    with op.batch_alter_table("lancamento_aula_aluno", schema=None) as batch_op:
        batch_op.alter_column("atestado", existing_type=sa.Boolean(), nullable=False)


def downgrade():
    with op.batch_alter_table("lancamento_aula_aluno", schema=None) as batch_op:
        batch_op.drop_column("atestado")

