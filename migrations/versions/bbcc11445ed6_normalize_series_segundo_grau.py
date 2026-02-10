"""normalize series segundo grau

Revision ID: bbcc11445ed6
Revises: 2f5111cc730b
Create Date: 2026-02-10 14:45:42.021290

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bbcc11445ed6'
down_revision = '2f5111cc730b'
branch_labels = None
depends_on = None


def upgrade():
    # Normalize stored values for "2º grau" series.
    op.execute("UPDATE turma SET serie = '1º Ano' WHERE serie = '1º SG'")
    op.execute("UPDATE turma SET serie = '2º Ano' WHERE serie = '2º SG'")

    # Rebuild the generated nome prefix if it used the old tokens.
    op.execute("UPDATE turma SET nome = replace(nome, '1º SG ', '1º Ano ') WHERE nome LIKE '1º SG %'")
    op.execute("UPDATE turma SET nome = replace(nome, '2º SG ', '2º Ano ') WHERE nome LIKE '2º SG %'")


def downgrade():
    op.execute("UPDATE turma SET serie = '1º SG' WHERE serie = '1º Ano'")
    op.execute("UPDATE turma SET serie = '2º SG' WHERE serie = '2º Ano'")

    op.execute("UPDATE turma SET nome = replace(nome, '1º Ano ', '1º SG ') WHERE nome LIKE '1º Ano %'")
    op.execute("UPDATE turma SET nome = replace(nome, '2º Ano ', '2º SG ') WHERE nome LIKE '2º Ano %'")
