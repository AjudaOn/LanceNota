from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin

from .extensions import db


class Professor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    escola = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Turma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("professor.id"), nullable=False, index=True)
    nome = db.Column(db.String(120), nullable=False)
    serie = db.Column(db.String(32), nullable=True)
    turma_letra = db.Column(db.String(4), nullable=True)
    periodo = db.Column(db.String(16), nullable=True)
    disciplina = db.Column(db.String(120), nullable=True)
    ano_serie = db.Column(db.String(120), nullable=True)
    ano_letivo = db.Column(db.Integer, nullable=False, default=2026)
    trimestre_atual = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TurmaHorario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey("turma.id"), nullable=False, index=True)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=Seg, 1=Ter, ..., 6=Dom
    hora = db.Column(db.String(5), nullable=False)  # HH:MM
    periodo = db.Column(db.String(16), nullable=False)  # Manhã | Tarde | Noite
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "turma_id",
            "dia_semana",
            "hora",
            "periodo",
            name="uq_turma_horario_dia_hora_periodo",
        ),
    )


class HorarioEvento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("professor.id"), nullable=False, index=True)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0=Seg, 1=Ter, ..., 6=Dom
    hora = db.Column(db.String(5), nullable=False)  # HH:MM
    periodo = db.Column(db.String(16), nullable=False)  # Manhã | Tarde | Noite
    titulo = db.Column(db.String(120), nullable=False)  # ex: HA
    subtitulo = db.Column(db.String(255), nullable=True)  # ex: Hora Atividade
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint(
            "professor_id",
            "dia_semana",
            "hora",
            "periodo",
            name="uq_horario_evento_slot",
        ),
    )


class Aluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey("turma.id"), nullable=False, index=True)
    nome_completo = db.Column(db.String(255), nullable=False)
    numero_chamada = db.Column(db.Integer, nullable=True)
    matricula = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(16), nullable=False, default="ativo")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Atividade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    turma_id = db.Column(db.Integer, db.ForeignKey("turma.id"), nullable=False, index=True)
    titulo = db.Column(db.String(255), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    data = db.Column(db.Date, nullable=True)
    trimestre = db.Column(db.Integer, nullable=False, default=1)
    peso = db.Column(db.Integer, nullable=False, default=1)
    nota_maxima = db.Column(db.Integer, nullable=False, default=10)
    aulas_planejadas = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(16), nullable=False, default="rascunho")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AvaliacaoAluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey("atividade.id"), nullable=False, index=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("aluno.id"), nullable=False, index=True)
    nota = db.Column(db.Float, nullable=True)
    comentario_curto = db.Column(db.String(255), nullable=True)
    comentario_longo = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("atividade_id", "aluno_id", name="uq_avaliacao_atividade_aluno"),)


class AtividadeAula(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    atividade_id = db.Column(db.Integer, db.ForeignKey("atividade.id"), nullable=False, index=True)
    numero = db.Column(db.Integer, nullable=False)
    data = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("atividade_id", "numero", name="uq_atividade_aula_numero"),
    )


class LancamentoAulaAluno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey("atividade_aula.id"), nullable=False, index=True)
    aluno_id = db.Column(db.Integer, db.ForeignKey("aluno.id"), nullable=False, index=True)
    nota = db.Column(db.Float, nullable=True)
    atestado = db.Column(db.Boolean, nullable=False, default=False)
    observacao = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("aula_id", "aluno_id", name="uq_lancamento_aula_aluno"),
    )
