"""normalize disciplina arte

Revision ID: b3bc29eea071
Revises: 053e63607ba2
Create Date: 2026-02-10 15:11:59.901198

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3bc29eea071'
down_revision = '053e63607ba2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE turma SET disciplina = 'Arte' WHERE disciplina = 'Artes'")
    op.execute("UPDATE turma SET nome = replace(nome, ' - Artes - ', ' - Arte - ') WHERE nome LIKE '% - Artes - %'")


def downgrade():
    op.execute("UPDATE turma SET disciplina = 'Artes' WHERE disciplina = 'Arte'")
    op.execute("UPDATE turma SET nome = replace(nome, ' - Arte - ', ' - Artes - ') WHERE nome LIKE '% - Arte - %'")
