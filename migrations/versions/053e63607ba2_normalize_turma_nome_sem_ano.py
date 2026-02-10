"""normalize turma nome sem ano

Revision ID: 053e63607ba2
Revises: bbcc11445ed6
Create Date: 2026-02-10 14:57:57.685673

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '053e63607ba2'
down_revision = 'bbcc11445ed6'
branch_labels = None
depends_on = None


def upgrade():
    # Keep `turma.serie` as "1º Ano"/"2º Ano", but the generated `turma.nome` should not include "Ano".
    op.execute("UPDATE turma SET nome = replace(nome, '1º Ano ', '1º ') WHERE nome LIKE '1º Ano %'")
    op.execute("UPDATE turma SET nome = replace(nome, '2º Ano ', '2º ') WHERE nome LIKE '2º Ano %'")


def downgrade():
    op.execute("UPDATE turma SET nome = replace(nome, '1º ', '1º Ano ') WHERE nome LIKE '1º %'")
    op.execute("UPDATE turma SET nome = replace(nome, '2º ', '2º Ano ') WHERE nome LIKE '2º %'")
