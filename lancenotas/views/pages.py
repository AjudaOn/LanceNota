from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date
from datetime import datetime

from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy import or_

from ..extensions import db
from ..constants import MAX_TRIMESTRE
from ..models import (
    Aluno,
    Atividade,
    AtividadeAula,
    DiarioAnotacao,
    Estudante,
    FechamentoTrimestreAluno,
    FechamentoTrimestreTurma,
    HorarioEvento,
    LancamentoAulaAluno,
    Turma,
    TurmaHorario,
)
from ..services.pdf_import import extract_resumo_registro_classe

pages_bp = Blueprint("pages", __name__)


def _safe_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _selected_ano_letivo(*, professor_id: int) -> int:
    raw = session.get("ano_letivo")
    if raw is not None:
        try:
            year = int(raw)
            if 2000 <= year <= 2100:
                return year
        except (TypeError, ValueError):
            pass

    max_year = (
        db.session.query(func.max(Turma.ano_letivo))
        .filter(Turma.professor_id == professor_id)
        .scalar()
    )
    year = int(max_year) if max_year is not None else int(date.today().year)
    session["ano_letivo"] = year
    return year


def _aulas_iniciadas_ids(*, aulas_ids: list[int], today: date) -> set[int]:
    if not aulas_ids:
        return set()

    started_ids: set[int] = set()

    started_rows = (
        db.session.query(AtividadeAula.id)
        .filter(AtividadeAula.id.in_(aulas_ids), AtividadeAula.data.isnot(None), AtividadeAula.data <= today)
        .all()
    )
    started_ids.update([int(r[0]) for r in started_rows])

    launched_rows = (
        db.session.query(LancamentoAulaAluno.aula_id)
        .filter(LancamentoAulaAluno.aula_id.in_(aulas_ids))
        .distinct()
        .all()
    )
    started_ids.update([int(r[0]) for r in launched_rows])

    return started_ids


def _validate_trimestre_completo_para_fechamento(*, turma: Turma, trimestre: int) -> str | None:
    alunos_ativos = Aluno.query.filter_by(turma_id=turma.id, status="ativo").all()
    if not alunos_ativos:
        return None

    ano_letivo = int(turma.ano_letivo or 2026)
    estudante_ids = [int(a.estudante_id) for a in alunos_ativos if a.estudante_id is not None]

    locked_estudantes_rows = (
        db.session.query(FechamentoTrimestreAluno.estudante_id)
        .filter_by(turma_id=turma.id, ano_letivo=ano_letivo, trimestre=trimestre, locked=True)
        .all()
    )
    locked_estudantes_ids = {int(r[0]) for r in locked_estudantes_rows if r[0] is not None}

    other_snapshot_estudantes_ids: set[int] = set()
    if estudante_ids:
        other_rows = (
            db.session.query(FechamentoTrimestreAluno.estudante_id)
            .filter(
                FechamentoTrimestreAluno.ano_letivo == ano_letivo,
                FechamentoTrimestreAluno.trimestre == trimestre,
                FechamentoTrimestreAluno.estudante_id.in_(estudante_ids),
                FechamentoTrimestreAluno.turma_id != int(turma.id),
            )
            .distinct()
            .all()
        )
        other_snapshot_estudantes_ids = {int(r[0]) for r in other_rows if r[0] is not None}

    alunos_requeridos = [
        a
        for a in alunos_ativos
        if a.estudante_id is None
        or (int(a.estudante_id) not in locked_estudantes_ids and int(a.estudante_id) not in other_snapshot_estudantes_ids)
    ]
    if not alunos_requeridos:
        return None

    atividades = Atividade.query.filter_by(turma_id=turma.id, trimestre=trimestre).all()
    if not atividades:
        return None

    aulas: list[AtividadeAula] = []
    for atv in atividades:
        aulas.extend(_ensure_aulas_for_atividade(atv))

    if not aulas:
        return None

    total_alunos = len(alunos_requeridos)
    aluno_ids = [int(a.id) for a in alunos_requeridos]
    aulas_ids = [int(a.id) for a in aulas]

    covered = (
        db.session.query(LancamentoAulaAluno.aula_id, func.count(func.distinct(LancamentoAulaAluno.aluno_id)))
        .filter(
            LancamentoAulaAluno.aula_id.in_(aulas_ids),
            LancamentoAulaAluno.aluno_id.in_(aluno_ids),
            or_(LancamentoAulaAluno.nota.isnot(None), LancamentoAulaAluno.atestado.is_(True)),
        )
        .group_by(LancamentoAulaAluno.aula_id)
        .all()
    )
    covered_by_aula: dict[int, int] = {int(aula_id): int(cnt) for aula_id, cnt in covered}

    atividade_title_by_id: dict[int, str] = {int(a.id): str(a.titulo) for a in atividades}
    aula_meta_by_id: dict[int, tuple[int, int]] = {int(a.id): (int(a.atividade_id), int(a.numero)) for a in aulas}

    issues: list[str] = []
    for aula_id in sorted(aulas_ids):
        cnt = int(covered_by_aula.get(int(aula_id), 0))
        if cnt >= total_alunos:
            continue
        missing = total_alunos - cnt
        atividade_id, aula_num = aula_meta_by_id.get(int(aula_id), (0, 0))
        titulo = atividade_title_by_id.get(int(atividade_id), "Atividade")
        issues.append(f"{titulo} (Aula {aula_num}): {missing} aluno(s) sem nota/atestado")
        if len(issues) >= 6:
            break

    if not issues:
        return None

    return "Não é possível fechar: faltam lançamentos neste trimestre. " + " | ".join(issues)


def _ensure_aulas_for_atividade(atividade: Atividade) -> list[AtividadeAula]:
    aulas = AtividadeAula.query.filter_by(atividade_id=atividade.id).order_by(AtividadeAula.numero.asc()).all()
    target = max(1, int(atividade.aulas_planejadas or 1))
    if len(aulas) >= target:
        return aulas

    existing_nums = {a.numero for a in aulas}
    for n in range(1, target + 1):
        if n in existing_nums:
            continue
        db.session.add(AtividadeAula(atividade_id=atividade.id, numero=n))
    db.session.commit()
    return AtividadeAula.query.filter_by(atividade_id=atividade.id).order_by(AtividadeAula.numero.asc()).all()


@pages_bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    return redirect(url_for("auth.login"))


@pages_bp.get("/dashboard")
@login_required
def dashboard():
    professor_id = int(current_user.id)
    today = date.today()

    ano_letivo = _selected_ano_letivo(professor_id=professor_id)
    turmas = Turma.query.filter_by(professor_id=professor_id, ano_letivo=ano_letivo).all()
    turma_ids = [t.id for t in turmas]

    turmas_ativas = len(turmas)

    if turma_ids:
        total_alunos = (
            db.session.query(func.count(Aluno.id))
            .filter(Aluno.turma_id.in_(turma_ids))
            .scalar()
            or 0
        )
    else:
        total_alunos = 0

    atividades = Atividade.query.filter(Atividade.turma_id.in_(turma_ids)).all() if turma_ids else []

    alunos_por_turma: dict[int, int] = {}
    if turma_ids:
        for turma_id, count in (
            db.session.query(Aluno.turma_id, func.count(Aluno.id))
            .filter(Aluno.turma_id.in_(turma_ids))
            .group_by(Aluno.turma_id)
            .all()
        ):
            alunos_por_turma[int(turma_id)] = int(count or 0)

    eligible_slots = 0
    for a in atividades:
        eligible_aulas = (
            AtividadeAula.query.filter_by(atividade_id=a.id)
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .count()
        )
        if eligible_aulas <= 0:
            continue
        eligible_slots += int(eligible_aulas) * int(alunos_por_turma.get(int(a.turma_id), 0))

    notas_count = 0
    atestados_count = 0
    if turma_ids and eligible_slots > 0:
        notas_count = (
            db.session.query(func.count(LancamentoAulaAluno.id))
            .join(AtividadeAula, LancamentoAulaAluno.aula_id == AtividadeAula.id)
            .join(Atividade, AtividadeAula.atividade_id == Atividade.id)
            .join(Turma, Atividade.turma_id == Turma.id)
            .filter(Turma.professor_id == professor_id)
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .filter(LancamentoAulaAluno.nota.isnot(None))
            .scalar()
            or 0
        )
        atestados_count = (
            db.session.query(func.count(LancamentoAulaAluno.id))
            .join(AtividadeAula, LancamentoAulaAluno.aula_id == AtividadeAula.id)
            .join(Atividade, AtividadeAula.atividade_id == Atividade.id)
            .join(Turma, Atividade.turma_id == Turma.id)
            .filter(Turma.professor_id == professor_id)
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .filter(LancamentoAulaAluno.atestado.is_(True))
            .scalar()
            or 0
        )

    avaliacoes_pendentes = max(0, int(eligible_slots) - int(notas_count) - int(atestados_count))

    # Desempenho (0-10): soma das notas lançadas / total de notas esperadas.
    # Nota não lançada conta como 0, então o denominador precisa considerar a carga planejada.
    desempenho_media: float | None = None
    denom = int(eligible_slots) - int(atestados_count)
    if turma_ids and denom > 0:
        sum_notas = (
            db.session.query(func.sum(LancamentoAulaAluno.nota))
            .join(AtividadeAula, LancamentoAulaAluno.aula_id == AtividadeAula.id)
            .join(Atividade, AtividadeAula.atividade_id == Atividade.id)
            .join(Turma, Atividade.turma_id == Turma.id)
            .filter(Turma.professor_id == professor_id)
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .filter(LancamentoAulaAluno.nota.isnot(None))
            .scalar()
            or 0.0
        )
        desempenho_media = round(float(sum_notas) / float(denom), 2)

    desempenho_por_turma: list[dict] = []
    if turma_ids:
        aulas_count_by_turma: dict[int, int] = {}
        for turma_id, aulas_count in (
            db.session.query(Atividade.turma_id, func.count(AtividadeAula.id))
            .join(AtividadeAula, AtividadeAula.atividade_id == Atividade.id)
            .filter(Atividade.turma_id.in_(turma_ids))
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .group_by(Atividade.turma_id)
            .all()
        ):
            aulas_count_by_turma[int(turma_id)] = int(aulas_count or 0)

        notas_sum_by_turma: dict[int, float] = {}
        notas_count_by_turma: dict[int, int] = {}
        for turma_id, sum_notas, count_notas in (
            db.session.query(Atividade.turma_id, func.sum(LancamentoAulaAluno.nota), func.count(LancamentoAulaAluno.id))
            .join(AtividadeAula, LancamentoAulaAluno.aula_id == AtividadeAula.id)
            .join(Atividade, AtividadeAula.atividade_id == Atividade.id)
            .filter(Atividade.turma_id.in_(turma_ids))
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .filter(LancamentoAulaAluno.nota.isnot(None))
            .group_by(Atividade.turma_id)
            .all()
        ):
            notas_sum_by_turma[int(turma_id)] = float(sum_notas or 0.0)
            notas_count_by_turma[int(turma_id)] = int(count_notas or 0)

        atestados_count_by_turma: dict[int, int] = {}
        for turma_id, count_atestados in (
            db.session.query(Atividade.turma_id, func.count(LancamentoAulaAluno.id))
            .join(AtividadeAula, LancamentoAulaAluno.aula_id == AtividadeAula.id)
            .join(Atividade, AtividadeAula.atividade_id == Atividade.id)
            .filter(Atividade.turma_id.in_(turma_ids))
            .filter(or_(AtividadeAula.data.is_(None), AtividadeAula.data <= today))
            .filter(LancamentoAulaAluno.atestado.is_(True))
            .group_by(Atividade.turma_id)
            .all()
        ):
            atestados_count_by_turma[int(turma_id)] = int(count_atestados or 0)

        for t in turmas:
            alunos_count = int(alunos_por_turma.get(int(t.id), 0))
            aulas_count = int(aulas_count_by_turma.get(int(t.id), 0))
            eligible_slots_turma = aulas_count * alunos_count
            notas_count_turma = int(notas_count_by_turma.get(int(t.id), 0))
            atestados_count_turma = int(atestados_count_by_turma.get(int(t.id), 0))
            pendentes_turma = max(0, eligible_slots_turma - notas_count_turma - atestados_count_turma)
            denom_turma = max(0, eligible_slots_turma - atestados_count_turma)
            media_turma = (
                round(float(notas_sum_by_turma.get(int(t.id), 0.0)) / float(denom_turma), 2)
                if denom_turma > 0
                else None
            )
            desempenho_por_turma.append(
                {
                    "id": int(t.id),
                    "nome": t.nome,
                    "serie": t.serie,
                    "turma_letra": t.turma_letra,
                    "disciplina": t.disciplina,
                    "alunos": alunos_count,
                    "media": media_turma,
                    "pendentes": pendentes_turma,
                }
            )

        desempenho_por_turma.sort(key=lambda x: (x["media"] is None, -(x["media"] or 0.0), x["nome"].lower()))

    return render_template(
        "pages/dashboard.html",
        selected_ano_letivo=ano_letivo,
        turmas_ativas=turmas_ativas,
        total_alunos=total_alunos,
        avaliacoes_pendentes=avaliacoes_pendentes,
        desempenho_media=desempenho_media,
        desempenho_por_turma=desempenho_por_turma,
    )


@pages_bp.route("/turmas", methods=["GET", "POST"])
@login_required
def turmas():
    if request.method == "POST":
        selected_year = _selected_ano_letivo(professor_id=int(current_user.id))
        turma_id_raw = (request.form.get("turma_id") or "").strip()
        serie = (request.form.get("serie") or "").strip()
        turma_letra = (request.form.get("turma_letra") or "").strip().upper()
        disciplina_raw = (request.form.get("disciplina") or "").strip()
        ano_letivo_raw = (request.form.get("ano_letivo") or "").strip()
        horarios_dias = request.form.getlist("horario_dia")
        horarios_horas = request.form.getlist("horario_hora")
        horarios_periodos = request.form.getlist("horario_periodo")

        if not serie or not turma_letra or not disciplina_raw:
            return (
                render_template(
                    "pages/turmas.html",
                    error="Preencha Série, Turma e Disciplina.",
                    q=(request.args.get("q") or "").strip().lower(),
                    selected_ano_letivo=selected_year,
                ),
                400,
            )

        allowed_series = {"5º", "6º", "7º", "8º", "9º", "1º Ano", "2º Ano"}
        allowed_turmas = set("ABCDEFGH")
        allowed_periodos = {"Manhã", "Tarde", "Noite"}

        if serie not in allowed_series:
            return render_template("pages/turmas.html", error="Série inválida.", selected_ano_letivo=selected_year), 400
        if turma_letra not in allowed_turmas:
            return render_template("pages/turmas.html", error="Turma inválida.", selected_ano_letivo=selected_year), 400

        try:
            ano_letivo = int(ano_letivo_raw) if ano_letivo_raw else 2026
        except ValueError:
            return render_template("pages/turmas.html", error="Ano letivo inválido.", selected_ano_letivo=selected_year), 400

        disciplina = "Arte" if disciplina_raw.strip().lower() == "artes" else disciplina_raw

        if serie.endswith("º") and serie[:-1].isdigit():
            ano_serie = f"{serie} Ano"
        elif serie in {"1º Ano", "2º Ano"}:
            ano_serie = "Segundo Grau"
        else:
            ano_serie = None

        allowed_weekdays = set(range(0, 7))
        time_pattern = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        parsed_horarios: list[tuple[int, str, str]] = []
        for dia_raw, hora_raw, periodo_raw in zip(horarios_dias, horarios_horas, horarios_periodos):
            dia_raw = (dia_raw or "").strip()
            hora_raw = (hora_raw or "").strip()
            periodo_raw = (periodo_raw or "").strip()
            if not dia_raw and not hora_raw and not periodo_raw:
                continue
            try:
                dia = int(dia_raw)
            except ValueError:
                continue
            if dia not in allowed_weekdays:
                continue
            if not time_pattern.match(hora_raw):
                continue
            if periodo_raw not in allowed_periodos:
                continue
            parsed_horarios.append((dia, hora_raw, periodo_raw))

        if not parsed_horarios:
            return (
                render_template(
                    "pages/turmas.html",
                    error="Adicione pelo menos um horário completo (dia, hora e período).",
                    q=(request.args.get("q") or "").strip().lower(),
                ),
                400,
            )

        period_order = {"Manhã": 0, "Tarde": 1, "Noite": 2}
        periodos_unicos = sorted({p for _, _, p in parsed_horarios}, key=lambda p: period_order.get(p, 99))
        periodo_display = periodos_unicos[0] if len(periodos_unicos) == 1 else "/".join(periodos_unicos)
        periodo_principal = periodos_unicos[0] if len(periodos_unicos) == 1 else None

        serie_nome = serie.removesuffix(" Ano") if serie in {"1º Ano", "2º Ano"} else serie
        nome = f"{serie_nome} {turma_letra} - {disciplina} - {periodo_display}"

        if turma_id_raw:
            try:
                turma_id_int = int(turma_id_raw)
            except ValueError:
                turma_id_int = 0

            turma = Turma.query.filter_by(id=turma_id_int, professor_id=int(current_user.id)).first()
            if turma is None:
                return render_template("pages/turmas.html", error="Turma não encontrada.", selected_ano_letivo=selected_year), 404

            turma.nome = nome
            turma.serie = serie
            turma.turma_letra = turma_letra
            turma.periodo = periodo_principal
            turma.disciplina = disciplina
            turma.ano_serie = ano_serie
            turma.ano_letivo = ano_letivo
            db.session.commit()

            TurmaHorario.query.filter_by(turma_id=turma.id).delete()
            for dia, hora, p in parsed_horarios:
                db.session.add(TurmaHorario(turma_id=turma.id, dia_semana=dia, hora=hora, periodo=p))
            db.session.commit()
        else:
            turma = Turma(
                professor_id=int(current_user.id),
                nome=nome,
                serie=serie,
                turma_letra=turma_letra,
                periodo=periodo_principal,
                disciplina=disciplina,
                ano_serie=ano_serie,
                ano_letivo=ano_letivo,
            )
            db.session.add(turma)
            db.session.commit()

            for dia, hora, p in parsed_horarios:
                db.session.add(TurmaHorario(turma_id=turma.id, dia_semana=dia, hora=hora, periodo=p))
            db.session.commit()

        return redirect(url_for("pages.turmas"))

    q = (request.args.get("q") or "").strip().lower()

    professor_id = int(current_user.id)
    ano_letivo = _selected_ano_letivo(professor_id=professor_id)
    turmas_db = Turma.query.filter_by(professor_id=professor_id, ano_letivo=ano_letivo).all()

    serie_rank_map = {"5º": 5, "6º": 6, "7º": 7, "8º": 8, "9º": 9, "1º Ano": 10, "2º Ano": 11}

    def sort_key(t: Turma) -> tuple:
        return (
            int(serie_rank_map.get((t.serie or "").strip(), 99)),
            (t.turma_letra or "").strip(),
            (t.disciplina or "").strip().lower(),
            (t.nome or "").strip().lower(),
            t.created_at,
        )

    turmas_db = sorted(turmas_db, key=sort_key)

    def matches_query(t: Turma) -> bool:
        if not q:
            return True
        if q in (t.nome or "").lower():
            return True
        if t.disciplina and q in t.disciplina.lower():
            return True
        return False

    turmas_filtered = [t for t in turmas_db if matches_query(t)]

    turma_ids = [t.id for t in turmas_filtered]
    horarios_by_turma: dict[int, list[dict]] = {}
    if turma_ids:
        horarios = (
            TurmaHorario.query.filter(TurmaHorario.turma_id.in_(turma_ids))
            .order_by(TurmaHorario.dia_semana.asc(), TurmaHorario.hora.asc())
            .all()
        )
        for h in horarios:
            horarios_by_turma.setdefault(int(h.turma_id), []).append(
                {"dia_semana": int(h.dia_semana), "hora": h.hora, "periodo": h.periodo}
            )

    turma_cards: list[dict] = []
    for t in turmas_filtered:
        alunos_count = Aluno.query.filter_by(turma_id=t.id, status="ativo").count()
        atividades_count = Atividade.query.filter_by(turma_id=t.id).count()
        turma_cards.append(
            {
                "id": t.id,
                "nome": t.nome,
                "disciplina": t.disciplina,
                "ano_serie": t.ano_serie,
                "serie": t.serie,
                "turma_letra": t.turma_letra,
                "ano_letivo": t.ano_letivo,
                "horarios": horarios_by_turma.get(int(t.id), []),
                "alunos_count": alunos_count,
                "atividades_count": atividades_count,
            }
        )

    return render_template(
        "pages/turmas.html",
        turmas=turma_cards,
        q=q,
        selected_ano_letivo=ano_letivo,
    )


@pages_bp.get("/turmas/<int:turma_id>")
@login_required
def turma_detail(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    today = date.today()
    ano_letivo = int(turma.ano_letivo or 2026)

    tab = (request.args.get("tab") or "detalhes").strip().lower()
    if tab not in {"detalhes", "atividades"}:
        tab = "detalhes"

    trimestre_param = (request.args.get("trimestre") or "").strip()
    if trimestre_param:
        try:
            current_trimestre = max(1, min(MAX_TRIMESTRE, int(trimestre_param)))
        except ValueError:
            current_trimestre = 1
    else:
        fechados = {
            int(r.trimestre)
            for r in FechamentoTrimestreTurma.query.filter_by(
                turma_id=turma.id, ano_letivo=ano_letivo, status="fechado"
            ).all()
        }
        current_trimestre = next(
            (tri for tri in range(1, MAX_TRIMESTRE + 1) if tri not in fechados),
            MAX_TRIMESTRE,
        )

    fechamento_rec = FechamentoTrimestreTurma.query.filter_by(
        turma_id=turma.id,
        ano_letivo=ano_letivo,
        trimestre=current_trimestre,
    ).first()
    fechamento_status = (
        {
            "status": fechamento_rec.status,
            "fechado_em": fechamento_rec.fechado_em,
            "reaberto_em": fechamento_rec.reaberto_em,
        }
        if fechamento_rec is not None
        else {"status": "aberto", "fechado_em": None, "reaberto_em": None}
    )

    alunos_count = Aluno.query.filter_by(turma_id=turma.id, status="ativo").count()
    atividades_count = Atividade.query.filter_by(turma_id=turma.id).count()
    alunos = (
        Aluno.query.filter_by(turma_id=turma.id, status="ativo")
        .order_by(Aluno.numero_chamada.asc(), Aluno.nome_completo.asc())
        .all()
    )
    turmas_destino = (
        Turma.query.filter_by(professor_id=int(current_user.id), ano_letivo=turma.ano_letivo)
        .filter(Turma.id != turma.id)
        .order_by(Turma.created_at.asc())
        .all()
    )

    detalhes_notas: dict[int, dict[str, float | None]] = {}
    atividades: list[Atividade] = []
    selected_atividade: Atividade | None = None
    selected_aulas: list[AtividadeAula] = []
    selected_aula_num = 1
    lancamentos_by_aluno: dict[int, LancamentoAulaAluno] = {}
    medias_by_aluno: dict[int, float] = {}

    if tab == "detalhes":
        all_atividades = Atividade.query.filter_by(turma_id=turma.id).order_by(Atividade.created_at.desc()).all()

        atividade_ids = [a.id for a in all_atividades] if all_atividades else []
        aulas = (
            AtividadeAula.query.filter(AtividadeAula.atividade_id.in_(atividade_ids)).all()
            if atividade_ids
            else []
        )

        aulas_ids = [int(a.id) for a in aulas]
        iniciadas_ids = _aulas_iniciadas_ids(aulas_ids=aulas_ids, today=today) if aulas_ids else set()
        eligible_aulas = [a for a in aulas if int(a.id) in iniciadas_ids]
        aula_ids = [a.id for a in eligible_aulas]
        lancamentos = (
            LancamentoAulaAluno.query.filter(LancamentoAulaAluno.aula_id.in_(aula_ids)).all()
            if aula_ids
            else []
        )

        aula_to_atividade: dict[int, int] = {int(a.id): int(a.atividade_id) for a in eligible_aulas}
        eligible_aulas_count_by_atividade: dict[int, int] = {}
        for a in eligible_aulas:
            eligible_aulas_count_by_atividade[int(a.atividade_id)] = eligible_aulas_count_by_atividade.get(int(a.atividade_id), 0) + 1

        sum_by_atividade_aluno: dict[tuple[int, int], float] = {}
        atestado_by_atividade_aluno: dict[tuple[int, int], int] = {}
        for l in lancamentos:
            atividade_id = aula_to_atividade.get(int(l.aula_id))
            if atividade_id is None:
                continue
            key = (atividade_id, int(l.aluno_id))
            if l.atestado:
                atestado_by_atividade_aluno[key] = atestado_by_atividade_aluno.get(key, 0) + 1
                continue
            if l.nota is None:
                continue
            sum_by_atividade_aluno[key] = sum_by_atividade_aluno.get(key, 0.0) + float(l.nota)

        atividades_by_trimestre: dict[int, list[Atividade]] = {tri: [] for tri in range(1, MAX_TRIMESTRE + 1)}
        for a in all_atividades:
            tri = int(a.trimestre or 1)
            tri = max(1, min(MAX_TRIMESTRE, tri))
            atividades_by_trimestre[tri].append(a)

        estudante_ids = [int(a.estudante_id) for a in alunos if a.estudante_id is not None]
        snapshot_rows = (
            FechamentoTrimestreAluno.query.filter_by(ano_letivo=ano_letivo)
            .filter(FechamentoTrimestreAluno.estudante_id.in_(estudante_ids))
            .all()
            if estudante_ids
            else []
        )
        # Prefer snapshot from this turma; otherwise fall back to the latest snapshot from any turma
        # (useful when a student was transferred after a trimester was closed in another turma).
        snapshot_best_by_estudante_tri: dict[tuple[int, int], FechamentoTrimestreAluno] = {}
        for r in snapshot_rows:
            key = (int(r.estudante_id), int(r.trimestre))
            current = snapshot_best_by_estudante_tri.get(key)
            if current is None:
                snapshot_best_by_estudante_tri[key] = r
                continue
            if int(r.turma_id) == int(turma.id) and int(current.turma_id) != int(turma.id):
                snapshot_best_by_estudante_tri[key] = r
                continue
            if int(r.turma_id) != int(turma.id) and int(current.turma_id) == int(turma.id):
                continue
            if getattr(r, "created_at", None) and getattr(current, "created_at", None):
                if r.created_at > current.created_at:
                    snapshot_best_by_estudante_tri[key] = r

        snapshot_media_by_estudante_tri: dict[tuple[int, int], float | None] = {
            key: (float(row.media_final) if row.media_final is not None else None)
            for key, row in snapshot_best_by_estudante_tri.items()
        }

        for aluno in alunos:
            aluno_row: dict[str, float | None] = {}
            trimestre_vals: list[float] = []

            for tri in range(1, MAX_TRIMESTRE + 1):
                snap_val = None
                if aluno.estudante_id is not None:
                    snap_val = snapshot_media_by_estudante_tri.get((int(aluno.estudante_id), tri))

                if snap_val is not None:
                    aluno_row[f"t{tri}"] = round(float(snap_val), 2)
                    trimestre_vals.append(float(snap_val))
                    continue

                tri_sum = 0.0
                tri_peso = 0.0
                for atv in atividades_by_trimestre[tri]:
                    eligible_cnt = int(eligible_aulas_count_by_atividade.get(int(atv.id), 0))
                    if eligible_cnt <= 0:
                        continue
                    atestados_cnt = int(atestado_by_atividade_aluno.get((int(atv.id), int(aluno.id)), 0))
                    denom = max(0, eligible_cnt - atestados_cnt)
                    if denom <= 0:
                        continue
                    media_atv = sum_by_atividade_aluno.get((int(atv.id), int(aluno.id)), 0.0) / float(denom)
                    peso = float(atv.peso or 1)
                    tri_sum += media_atv * peso
                    tri_peso += peso

                tri_val = round(tri_sum / tri_peso, 2) if tri_peso > 0 else None
                aluno_row[f"t{tri}"] = tri_val
                if tri_val is not None:
                    trimestre_vals.append(float(tri_val))

            aluno_row["total"] = round(sum(trimestre_vals) / float(len(trimestre_vals)), 2) if trimestre_vals else None
            detalhes_notas[int(aluno.id)] = aluno_row

    if tab == "atividades":
        atividades = (
            Atividade.query.filter_by(turma_id=turma.id, trimestre=current_trimestre)
            .order_by(Atividade.created_at.desc())
            .all()
        )

        atividade_id = request.args.get("atividade_id")
        if atividade_id:
            selected_atividade = next((a for a in atividades if str(a.id) == str(atividade_id)), None)
        if selected_atividade is None and atividades:
            selected_atividade = atividades[0]

        if selected_atividade is not None:
            selected_aulas = _ensure_aulas_for_atividade(selected_atividade)
            selected_aula_num = max(1, min(len(selected_aulas) or 1, _safe_int(request.args.get("aula"), 1)))
            selected_aula = next((a for a in selected_aulas if a.numero == selected_aula_num), None)

            if selected_aula is not None:
                lancamentos = LancamentoAulaAluno.query.filter_by(aula_id=selected_aula.id).all()
                lancamentos_by_aluno = {l.aluno_id: l for l in lancamentos}

            selected_aulas_ids = [int(a.id) for a in selected_aulas]
            iniciadas_ids = _aulas_iniciadas_ids(aulas_ids=selected_aulas_ids, today=today)
            eligible_aulas_for_media = [a for a in selected_aulas if int(a.id) in iniciadas_ids]
            aulas_ids = [a.id for a in eligible_aulas_for_media]
            all_lancamentos = (
                LancamentoAulaAluno.query.filter(LancamentoAulaAluno.aula_id.in_(aulas_ids)).all()
                if aulas_ids
                else []
            )

            nota_by_aula_aluno: dict[tuple[int, int], float] = {}
            atestado_by_aula_aluno: set[tuple[int, int]] = set()
            for l in all_lancamentos:
                if l.atestado:
                    atestado_by_aula_aluno.add((l.aula_id, l.aluno_id))
                    continue
                if l.nota is None:
                    continue
                nota_by_aula_aluno[(l.aula_id, l.aluno_id)] = float(l.nota)

            for aluno in alunos:
                total = 0.0
                denom = 0
                for aula in eligible_aulas_for_media:
                    if (aula.id, aluno.id) in atestado_by_aula_aluno:
                        continue
                    denom += 1
                    total += nota_by_aula_aluno.get((aula.id, aluno.id), 0.0)
                medias_by_aluno[aluno.id] = round(total / float(denom), 2) if denom > 0 else None

    return render_template(
        "pages/turma_detail.html",
        turma=turma,
        current_turma={"id": turma.id, "nome": turma.nome},
        tab=tab,
        current_trimestre=current_trimestre,
        fechamento_status=fechamento_status,
        alunos_count=alunos_count,
        atividades_count=atividades_count,
        alunos=alunos,
        atividades=atividades,
        selected_atividade=selected_atividade,
        selected_aulas=selected_aulas,
        selected_aula_num=selected_aula_num,
        lancamentos_by_aluno=lancamentos_by_aluno,
        medias_by_aluno=medias_by_aluno,
        detalhes_notas=detalhes_notas,
        error=(request.args.get("error") or "").strip(),
        transfer_ok=(request.args.get("transfer_ok") or "").strip(),
        imported=request.args.get("imported"),
        import_status=request.args.get("import_status"),
        import_mismatch=(request.args.get("import_mismatch") or "").strip(),
        turmas_destino=turmas_destino,
    )


@pages_bp.post("/turmas/<int:turma_id>/delete")
@login_required
def turma_delete(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    try:
        db.session.delete(turma)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return redirect(url_for("pages.turmas", error="Não foi possível deletar a turma."))

    return redirect(url_for("pages.turmas"))


@pages_bp.post("/turmas/<int:turma_id>/atividades")
@login_required
def turma_criar_atividade(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), 1)))
    titulo = (request.form.get("titulo") or "").strip()
    descricao = (request.form.get("descricao") or "").strip() or None
    aulas_planejadas = max(1, _safe_int(request.form.get("aulas_planejadas"), 1))

    if not titulo:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, trimestre=trimestre))

    atividade = Atividade(
        turma_id=turma.id,
        titulo=titulo,
        descricao=descricao,
        trimestre=trimestre,
        aulas_planejadas=aulas_planejadas,
        nota_maxima=10,
        status="ativa",
    )
    db.session.add(atividade)
    db.session.commit()

    for n in range(1, aulas_planejadas + 1):
        date_str = (request.form.get(f"data_aula_{n}") or "").strip()
        aula_date = None
        if date_str:
            try:
                aula_date = date.fromisoformat(date_str)
            except ValueError:
                aula_date = None
        db.session.add(AtividadeAula(atividade_id=atividade.id, numero=n, data=aula_date))
    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab="atividades",
            trimestre=trimestre,
            atividade_id=atividade.id,
            aula=1,
        )
    )


@pages_bp.post("/turmas/<int:turma_id>/atividades/<int:atividade_id>/planejamento")
@login_required
def turma_planejar_atividade(turma_id: int, atividade_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    atividade = Atividade.query.filter_by(id=atividade_id, turma_id=turma.id).first()
    if atividade is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
    aulas_planejadas = max(1, _safe_int(request.form.get("aulas_planejadas"), atividade.aulas_planejadas or 1))

    aulas = AtividadeAula.query.filter_by(atividade_id=atividade.id).order_by(AtividadeAula.numero.asc()).all()
    current_count = len(aulas)

    if aulas_planejadas < current_count:
        aulas_to_remove = [a for a in aulas if a.numero > aulas_planejadas]
        if not aulas_to_remove:
            atividade.aulas_planejadas = aulas_planejadas
        else:
            ids = [a.id for a in aulas_to_remove]
            used = (
                LancamentoAulaAluno.query.filter(LancamentoAulaAluno.aula_id.in_(ids)).first()
                is not None
            )
            if used:
                return redirect(
                    url_for(
                        "pages.turma_detail",
                        turma_id=turma_id,
                        tab="atividades",
                        trimestre=trimestre,
                        atividade_id=atividade.id,
                        error="Não é possível reduzir o número de aulas: há lançamentos nas aulas finais.",
                    )
                )
            for a in aulas_to_remove:
                db.session.delete(a)

    if aulas_planejadas > current_count:
        for n in range(current_count + 1, aulas_planejadas + 1):
            db.session.add(AtividadeAula(atividade_id=atividade.id, numero=n))

    atividade.trimestre = trimestre
    atividade.aulas_planejadas = aulas_planejadas

    for n in range(1, aulas_planejadas + 1):
        date_str = (request.form.get(f"data_aula_{n}") or "").strip()
        aula = AtividadeAula.query.filter_by(atividade_id=atividade.id, numero=n).first()
        if aula is None:
            continue
        if not date_str:
            aula.data = None
            continue
        try:
            aula.data = date.fromisoformat(date_str)
        except ValueError:
            pass

    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab="atividades",
            trimestre=trimestre,
            atividade_id=atividade.id,
            aula=1,
        )
    )


@pages_bp.post("/turmas/<int:turma_id>/atividades/<int:atividade_id>/configuracao")
@login_required
def turma_configurar_atividade(turma_id: int, atividade_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    atividade = Atividade.query.filter_by(id=atividade_id, turma_id=turma.id).first()
    if atividade is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, tab="atividades"))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
    aula_num = max(1, _safe_int(request.form.get("aula"), 1))

    titulo = (request.form.get("titulo") or "").strip()
    descricao = (request.form.get("descricao") or "").strip() or None
    aulas_planejadas = max(1, _safe_int(request.form.get("aulas_planejadas"), atividade.aulas_planejadas or 1))

    if not titulo:
        return redirect(
            url_for(
                "pages.turma_detail",
                turma_id=turma_id,
                tab="atividades",
                trimestre=trimestre,
                atividade_id=atividade.id,
                aula=aula_num,
                error="Informe um nome para a atividade.",
            )
        )

    aulas = AtividadeAula.query.filter_by(atividade_id=atividade.id).order_by(AtividadeAula.numero.asc()).all()
    current_count = len(aulas)

    if aulas_planejadas < current_count:
        aulas_to_remove = [a for a in aulas if a.numero > aulas_planejadas]
        if aulas_to_remove:
            ids = [a.id for a in aulas_to_remove]
            used = (
                LancamentoAulaAluno.query.filter(LancamentoAulaAluno.aula_id.in_(ids)).first()
                is not None
            )
            if used:
                return redirect(
                    url_for(
                        "pages.turma_detail",
                        turma_id=turma_id,
                        tab="atividades",
                        trimestre=trimestre,
                        atividade_id=atividade.id,
                        aula=aula_num,
                        error="Não é possível reduzir o número de aulas: há lançamentos nas aulas finais.",
                    )
                )
            for a in aulas_to_remove:
                db.session.delete(a)

    if aulas_planejadas > current_count:
        for n in range(current_count + 1, aulas_planejadas + 1):
            db.session.add(AtividadeAula(atividade_id=atividade.id, numero=n))

    atividade.titulo = titulo
    atividade.descricao = descricao
    atividade.trimestre = trimestre
    atividade.aulas_planejadas = aulas_planejadas

    for n in range(1, aulas_planejadas + 1):
        date_str = (request.form.get(f"data_aula_{n}") or "").strip()
        aula = AtividadeAula.query.filter_by(atividade_id=atividade.id, numero=n).first()
        if aula is None:
            continue
        if not date_str:
            aula.data = None
            continue
        try:
            aula.data = date.fromisoformat(date_str)
        except ValueError:
            pass

    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab="atividades",
            trimestre=trimestre,
            atividade_id=atividade.id,
            aula=aula_num,
        )
    )


@pages_bp.post("/turmas/<int:turma_id>/atividades/<int:atividade_id>/editar")
@login_required
def turma_editar_atividade(turma_id: int, atividade_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    atividade = Atividade.query.filter_by(id=atividade_id, turma_id=turma.id).first()
    if atividade is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, tab="atividades"))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
    aula_num = max(1, _safe_int(request.form.get("aula"), 1))

    titulo = (request.form.get("titulo") or "").strip()
    descricao = (request.form.get("descricao") or "").strip() or None

    if not titulo:
        return redirect(
            url_for(
                "pages.turma_detail",
                turma_id=turma_id,
                tab="atividades",
                trimestre=trimestre,
                atividade_id=atividade.id,
                aula=aula_num,
                error="Informe um nome para a atividade.",
            )
        )

    atividade.titulo = titulo
    atividade.descricao = descricao
    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab="atividades",
            trimestre=trimestre,
            atividade_id=atividade.id,
            aula=aula_num,
        )
    )


@pages_bp.post("/turmas/<int:turma_id>/atividades/<int:atividade_id>/lancamentos/<int:aula_num>")
@login_required
def turma_salvar_lancamentos(turma_id: int, atividade_id: int, aula_num: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    atividade = Atividade.query.filter_by(id=atividade_id, turma_id=turma.id).first()
    if atividade is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
    aula = AtividadeAula.query.filter_by(atividade_id=atividade.id, numero=aula_num).first()
    if aula is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, trimestre=trimestre, atividade_id=atividade.id))

    alunos = Aluno.query.filter_by(turma_id=turma.id).all()
    for aluno in alunos:
        nota_str = (request.form.get(f"nota_{aluno.id}") or "").strip()
        atestado_checked = (request.form.get(f"atestado_{aluno.id}") or "").strip().lower() in {"1", "true", "on", "yes"}
        obs_str = (request.form.get(f"obs_{aluno.id}") or "").strip()

        atestado = bool(atestado_checked)
        nota = None
        if nota_str != "":
            if nota_str.strip().upper() == "A":
                atestado = True
                nota = None
            elif not atestado:
                try:
                    nota_val = float(nota_str.replace(",", "."))
                    nota = max(0.0, min(10.0, nota_val))
                except ValueError:
                    return redirect(
                        url_for(
                            "pages.turma_detail",
                            turma_id=turma_id,
                            tab="atividades",
                            trimestre=trimestre,
                            atividade_id=atividade.id,
                            aula=aula_num,
                            error="Valor inválido em nota. Use 0–10 ou 'A' (atestado).",
                        )
                    )

        lanc = LancamentoAulaAluno.query.filter_by(aula_id=aula.id, aluno_id=aluno.id).first()
        has_any_value = bool(atestado) or (nota is not None) or (obs_str != "")
        if not has_any_value:
            if lanc is not None:
                db.session.delete(lanc)
            continue

        if lanc is None:
            lanc = LancamentoAulaAluno(aula_id=aula.id, aluno_id=aluno.id)
            db.session.add(lanc)
        lanc.nota = nota
        lanc.atestado = atestado
        lanc.observacao = obs_str or None

    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab="atividades",
            trimestre=trimestre,
            atividade_id=atividade.id,
            aula=aula_num,
        )
    )


@pages_bp.post("/turmas/<int:turma_id>/importar-alunos-pdf")
@login_required
def turma_importar_alunos_pdf(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    tab = (request.form.get("tab") or request.args.get("tab") or "detalhes").strip().lower()
    if tab not in {"detalhes", "atividades"}:
        tab = "detalhes"

    uploaded = request.files.get("pdf")
    if uploaded is None or uploaded.filename is None or uploaded.filename.strip() == "":
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, tab=tab, import_status="missing"))

    filename = uploaded.filename.lower()
    if not filename.endswith(".pdf"):
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, tab=tab, import_status="invalid"))

    import os  # noqa: PLC0415
    import uuid  # noqa: PLC0415
    from flask import current_app  # noqa: PLC0415
    from werkzeug.utils import secure_filename  # noqa: PLC0415

    uploads_dir = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    safe_name = secure_filename(uploaded.filename) or "lista.pdf"
    temp_name = f"{uuid.uuid4().hex}_{safe_name}"
    temp_path = os.path.join(uploads_dir, temp_name)
    uploaded.save(temp_path)

    try:
        info, students = extract_resumo_registro_classe(temp_path)
    except Exception:
        return redirect(url_for("pages.turma_detail", turma_id=turma_id, tab=tab, import_status="parse_error"))
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    existing_names = {
        a.nome_completo.strip().lower()
        for a in Aluno.query.filter_by(turma_id=turma_id).all()
        if a.nome_completo
    }

    created = 0
    for s in students:
        name_key = s.nome.strip().lower()
        if not name_key or name_key in existing_names:
            continue
        estudante = Estudante(
            nome_completo=s.nome,
            matricula=None,
        )
        db.session.add(estudante)
        db.session.flush()
        aluno = Aluno(
            turma_id=turma_id,
            estudante_id=estudante.id,
            nome_completo=s.nome,
            numero_chamada=s.numero_chamada,
            status="ativo",
        )
        db.session.add(aluno)
        existing_names.add(name_key)
        created += 1

    db.session.commit()

    # Basic mismatch check (only if we could parse turma info from PDF)
    def _norm_text(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()
        return normalized

    mismatch_fields: list[str] = []
    if info.serie and turma.serie and _norm_text(info.serie) != _norm_text(turma.serie):
        mismatch_fields.append("serie")
    if info.turma_letra and turma.turma_letra and _norm_text(info.turma_letra) != _norm_text(turma.turma_letra):
        mismatch_fields.append("turma")
    if info.periodo:
        horarios_periodos = {
            _norm_text(h.periodo)
            for h in TurmaHorario.query.filter_by(turma_id=turma_id).all()
            if h.periodo
        }
        periodo_pdf = _norm_text(info.periodo)
        if horarios_periodos:
            if periodo_pdf not in horarios_periodos:
                mismatch_fields.append("periodo")
        elif turma.periodo and periodo_pdf != _norm_text(turma.periodo):
            mismatch_fields.append("periodo")
    if info.ano_letivo and turma.ano_letivo and info.ano_letivo != turma.ano_letivo:
        mismatch_fields.append("ano_letivo")
    if info.disciplina and turma.disciplina:
        disciplina_pdf = _norm_text(info.disciplina).removesuffix("s")
        disciplina_db = _norm_text(turma.disciplina).removesuffix("s")
        if disciplina_pdf != disciplina_db:
            mismatch_fields.append("disciplina")

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_id,
            tab=tab,
            imported=created,
            import_status=("ok_mismatch" if mismatch_fields else "ok"),
            import_mismatch=",".join(mismatch_fields) if mismatch_fields else "",
        )
    )


@pages_bp.get("/atividades")
@login_required
def atividades():
    return render_template("pages/atividades.html")


@pages_bp.get("/fechamento")
@login_required
def fechamento():
    professor_id = int(current_user.id)
    turmas = Turma.query.filter_by(professor_id=professor_id).order_by(Turma.created_at.desc()).all()

    turma_id = request.args.get("turma_id")
    selected_turma: Turma | None = None
    if turma_id:
        try:
            turma_id_int = int(turma_id)
        except ValueError:
            turma_id_int = 0
        selected_turma = next((t for t in turmas if int(t.id) == int(turma_id_int)), None)
    if selected_turma is None and turmas:
        selected_turma = turmas[0]

    trimestre = request.args.get("trimestre")
    current_trimestre = (
        max(1, min(MAX_TRIMESTRE, _safe_int(trimestre, 1)))
        if trimestre
        else (selected_turma.trimestre_atual if selected_turma else 1)
    )
    current_trimestre = max(1, min(MAX_TRIMESTRE, int(current_trimestre)))

    fechamento_status: dict | None = None
    if selected_turma is not None:
        rec = FechamentoTrimestreTurma.query.filter_by(
            turma_id=selected_turma.id,
            ano_letivo=int(selected_turma.ano_letivo or 2026),
            trimestre=int(current_trimestre),
        ).first()
        if rec is not None:
            fechamento_status = {
                "status": rec.status,
                "fechado_em": rec.fechado_em,
                "reaberto_em": rec.reaberto_em,
            }

    return render_template(
        "pages/fechamento.html",
        turmas=turmas,
        selected_turma=selected_turma,
        current_trimestre=int(current_trimestre),
        fechamento_status=fechamento_status,
        error=(request.args.get("error") or "").strip(),
    )


def _build_fechamento_snapshots(*, turma: Turma, trimestre: int) -> int:
    today = date.today()
    ano_letivo = int(turma.ano_letivo or 2026)

    alunos = Aluno.query.filter_by(turma_id=turma.id, status="ativo").all()
    if not alunos:
        return 0

    estudante_ids = [int(a.estudante_id) for a in alunos if a.estudante_id is not None]
    other_snapshot_rows = (
        FechamentoTrimestreAluno.query.filter(
            FechamentoTrimestreAluno.ano_letivo == ano_letivo,
            FechamentoTrimestreAluno.trimestre == trimestre,
            FechamentoTrimestreAluno.estudante_id.in_(estudante_ids),
            FechamentoTrimestreAluno.turma_id != int(turma.id),
        ).all()
        if estudante_ids
        else []
    )
    # Best snapshot per estudante (used for transferred students)
    other_best_by_estudante: dict[int, FechamentoTrimestreAluno] = {}
    for r in other_snapshot_rows:
        sid = int(r.estudante_id)
        current = other_best_by_estudante.get(sid)
        if current is None:
            other_best_by_estudante[sid] = r
            continue
        if getattr(r, "created_at", None) and getattr(current, "created_at", None):
            if r.created_at > current.created_at:
                other_best_by_estudante[sid] = r

    atividades = Atividade.query.filter_by(turma_id=turma.id, trimestre=trimestre).all()
    if not atividades:
        for a in alunos:
            if a.estudante_id is None:
                continue

            best_other = other_best_by_estudante.get(int(a.estudante_id))
            if best_other is not None:
                existing_dest = FechamentoTrimestreAluno.query.filter_by(
                    turma_id=turma.id, estudante_id=a.estudante_id, ano_letivo=ano_letivo, trimestre=trimestre
                ).first()
                if existing_dest is None:
                    db.session.add(
                        FechamentoTrimestreAluno(
                            turma_id=turma.id,
                            estudante_id=a.estudante_id,
                            origem_turma_id=int(best_other.turma_id),
                            ano_letivo=ano_letivo,
                            trimestre=trimestre,
                            media_final=best_other.media_final,
                            total_pontos=best_other.total_pontos,
                            avaliadas=int(best_other.avaliadas or 0),
                            total_previstas=int(best_other.total_previstas or 0),
                            locked=True,
                            created_at=datetime.utcnow(),
                        )
                    )
                continue

            existing = FechamentoTrimestreAluno.query.filter_by(
                turma_id=turma.id, estudante_id=a.estudante_id, ano_letivo=ano_letivo, trimestre=trimestre
            ).first()
            if existing is None:
                db.session.add(
                    FechamentoTrimestreAluno(
                        turma_id=turma.id,
                        estudante_id=a.estudante_id,
                        ano_letivo=ano_letivo,
                        trimestre=trimestre,
                        media_final=None,
                        total_pontos=None,
                        avaliadas=0,
                        total_previstas=0,
                        created_at=datetime.utcnow(),
                    )
                )
        db.session.flush()
        return len([a for a in alunos if a.estudante_id is not None])

    atividade_ids = [a.id for a in atividades]
    aulas = AtividadeAula.query.filter(AtividadeAula.atividade_id.in_(atividade_ids)).all()
    aulas_ids = [int(a.id) for a in aulas]
    iniciadas_ids = _aulas_iniciadas_ids(aulas_ids=aulas_ids, today=today)
    eligible_aulas = [a for a in aulas if int(a.id) in iniciadas_ids]

    aula_to_atividade: dict[int, int] = {int(a.id): int(a.atividade_id) for a in eligible_aulas}
    eligible_aulas_count_by_atividade: dict[int, int] = {}
    for a in eligible_aulas:
        eligible_aulas_count_by_atividade[int(a.atividade_id)] = eligible_aulas_count_by_atividade.get(int(a.atividade_id), 0) + 1

    aula_ids = [a.id for a in eligible_aulas]
    lancamentos = (
        LancamentoAulaAluno.query.filter(LancamentoAulaAluno.aula_id.in_(aula_ids)).all()
        if aula_ids
        else []
    )

    sum_by_atividade_aluno: dict[tuple[int, int], float] = {}
    atestado_by_atividade_aluno: dict[tuple[int, int], int] = {}
    avaliadas_by_aluno: dict[int, int] = {}

    for l in lancamentos:
        atividade_id = aula_to_atividade.get(int(l.aula_id))
        if atividade_id is None:
            continue
        key = (atividade_id, int(l.aluno_id))
        if l.atestado:
            atestado_by_atividade_aluno[key] = atestado_by_atividade_aluno.get(key, 0) + 1
            continue
        if l.nota is None:
            continue
        sum_by_atividade_aluno[key] = sum_by_atividade_aluno.get(key, 0.0) + float(l.nota)
        avaliadas_by_aluno[int(l.aluno_id)] = avaliadas_by_aluno.get(int(l.aluno_id), 0) + 1

    peso_by_atividade: dict[int, float] = {int(a.id): float(a.peso or 1) for a in atividades}

    snapshots = 0
    for aluno in alunos:
        if aluno.estudante_id is None:
            continue

        best_other = other_best_by_estudante.get(int(aluno.estudante_id))
        if best_other is not None:
            existing_dest = FechamentoTrimestreAluno.query.filter_by(
                turma_id=turma.id, estudante_id=aluno.estudante_id, ano_letivo=ano_letivo, trimestre=trimestre
            ).first()
            if existing_dest is None:
                db.session.add(
                    FechamentoTrimestreAluno(
                        turma_id=turma.id,
                        estudante_id=aluno.estudante_id,
                        origem_turma_id=int(best_other.turma_id),
                        ano_letivo=ano_letivo,
                        trimestre=trimestre,
                        media_final=best_other.media_final,
                        total_pontos=best_other.total_pontos,
                        avaliadas=int(best_other.avaliadas or 0),
                        total_previstas=int(best_other.total_previstas or 0),
                        locked=True,
                        created_at=datetime.utcnow(),
                    )
                )
            else:
                # Keep transferred snapshot locked and sourced from origin
                existing_dest.media_final = best_other.media_final
                existing_dest.total_pontos = best_other.total_pontos
                existing_dest.avaliadas = int(best_other.avaliadas or 0)
                existing_dest.total_previstas = int(best_other.total_previstas or 0)
                existing_dest.origem_turma_id = int(best_other.turma_id)
                existing_dest.locked = True

            snapshots += 1
            continue

        tri_sum = 0.0
        tri_peso = 0.0
        total_previstas = 0
        total_pontos = 0.0

        for atv in atividades:
            eligible_cnt = int(eligible_aulas_count_by_atividade.get(int(atv.id), 0))
            if eligible_cnt <= 0:
                continue
            atestados_cnt = int(atestado_by_atividade_aluno.get((int(atv.id), int(aluno.id)), 0))
            denom = max(0, eligible_cnt - atestados_cnt)
            if denom <= 0:
                continue

            total_previstas += denom

            sum_notas = float(sum_by_atividade_aluno.get((int(atv.id), int(aluno.id)), 0.0))
            total_pontos += sum_notas

            media_atv = sum_notas / float(denom)
            peso = float(peso_by_atividade.get(int(atv.id), 1.0))
            tri_sum += media_atv * peso
            tri_peso += peso

        media_final = round(tri_sum / tri_peso, 2) if tri_peso > 0 else None
        total_pontos_val = round(total_pontos, 2) if total_previstas > 0 else None
        avaliadas = int(avaliadas_by_aluno.get(int(aluno.id), 0))

        existing = FechamentoTrimestreAluno.query.filter_by(
            turma_id=turma.id, estudante_id=aluno.estudante_id, ano_letivo=ano_letivo, trimestre=trimestre
        ).first()
        if existing is None:
            db.session.add(
                FechamentoTrimestreAluno(
                    turma_id=turma.id,
                    estudante_id=aluno.estudante_id,
                    origem_turma_id=None,
                    ano_letivo=ano_letivo,
                    trimestre=trimestre,
                    media_final=media_final,
                    total_pontos=total_pontos_val,
                    avaliadas=avaliadas,
                    total_previstas=total_previstas,
                    locked=False,
                    created_at=datetime.utcnow(),
                )
            )
        elif bool(getattr(existing, "locked", False)):
            snapshots += 1
            continue
        else:
            existing.media_final = media_final
            existing.total_pontos = total_pontos_val
            existing.avaliadas = avaliadas
            existing.total_previstas = total_previstas
            existing.origem_turma_id = None
            existing.locked = False

        snapshots += 1

    db.session.flush()
    return snapshots


@pages_bp.post("/fechamento/fechar")
@login_required
def fechamento_fechar():
    professor_id = int(current_user.id)
    turma_id = _safe_int(request.form.get("turma_id"), 0)
    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), 1)))

    turma = Turma.query.filter_by(id=turma_id, professor_id=professor_id).first()
    if turma is None:
        return redirect(url_for("pages.fechamento", error="Turma não encontrada."))

    validation_error = _validate_trimestre_completo_para_fechamento(turma=turma, trimestre=trimestre)
    if validation_error:
        if (request.form.get("return_to") or "").strip() == "turma_detail":
            return redirect(
                url_for("pages.turma_detail", turma_id=turma.id, tab="detalhes", trimestre=trimestre, error=validation_error)
            )
        return redirect(url_for("pages.fechamento", turma_id=turma.id, trimestre=trimestre, error=validation_error))

    ano_letivo = int(turma.ano_letivo or 2026)

    rec = FechamentoTrimestreTurma.query.filter_by(turma_id=turma.id, ano_letivo=ano_letivo, trimestre=trimestre).first()
    if rec is None:
        rec = FechamentoTrimestreTurma(
            turma_id=turma.id,
            ano_letivo=ano_letivo,
            trimestre=trimestre,
            status="aberto",
            created_at=datetime.utcnow(),
        )
        db.session.add(rec)
        db.session.flush()

    snapshots = _build_fechamento_snapshots(turma=turma, trimestre=trimestre)

    rec.status = "fechado"
    rec.fechado_em = datetime.utcnow()
    rec.fechado_por_professor_id = professor_id
    rec.reaberto_em = None

    if int(turma.trimestre_atual or 1) == int(trimestre):
        turma.trimestre_atual = min(MAX_TRIMESTRE, int(trimestre) + 1)

    db.session.commit()

    if (request.form.get("return_to") or "").strip() == "turma_detail":
        return redirect(url_for("pages.turma_detail", turma_id=turma.id, tab="detalhes", trimestre=trimestre))

    return redirect(url_for("pages.fechamento", turma_id=turma.id, trimestre=trimestre))


@pages_bp.post("/fechamento/reabrir")
@login_required
def fechamento_reabrir():
    professor_id = int(current_user.id)
    turma_id = _safe_int(request.form.get("turma_id"), 0)
    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), 1)))

    turma = Turma.query.filter_by(id=turma_id, professor_id=professor_id).first()
    if turma is None:
        return redirect(url_for("pages.fechamento", error="Turma não encontrada."))

    ano_letivo = int(turma.ano_letivo or 2026)
    rec = FechamentoTrimestreTurma.query.filter_by(turma_id=turma.id, ano_letivo=ano_letivo, trimestre=trimestre).first()
    if rec is None:
        return redirect(url_for("pages.fechamento", turma_id=turma.id, trimestre=trimestre, error="Trimestre ainda não foi fechado."))

    rec.status = "aberto"
    rec.reaberto_em = datetime.utcnow()
    db.session.commit()

    if (request.form.get("return_to") or "").strip() == "turma_detail":
        return redirect(url_for("pages.turma_detail", turma_id=turma.id, tab="detalhes", trimestre=trimestre))

    return redirect(url_for("pages.fechamento", turma_id=turma.id, trimestre=trimestre))


@pages_bp.post("/turmas/<int:turma_id>/transferir-aluno")
@login_required
def turma_transferir_aluno(turma_id: int):
    professor_id = int(current_user.id)
    turma_origem = Turma.query.filter_by(id=turma_id, professor_id=professor_id).first()
    if turma_origem is None:
        return redirect(url_for("pages.turmas"))

    trimestre = max(1, min(MAX_TRIMESTRE, _safe_int(request.form.get("trimestre"), 1)))
    aluno_id = _safe_int(request.form.get("aluno_id"), 0)
    turma_destino_id = _safe_int(request.form.get("turma_destino_id"), 0)

    if turma_destino_id <= 0 or turma_destino_id == int(turma_origem.id):
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Selecione a turma de destino."))

    turma_destino = Turma.query.filter_by(id=turma_destino_id, professor_id=professor_id).first()
    if turma_destino is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Turma de destino não encontrada."))

    if str(turma_destino.ano_letivo) != str(turma_origem.ano_letivo):
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="A turma de destino deve ser do mesmo ano letivo."))

    aluno = Aluno.query.filter_by(id=aluno_id, turma_id=turma_origem.id, status="ativo").first()
    if aluno is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Aluno não encontrado."))

    if aluno.estudante_id is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Este aluno não possui vínculo global (Estudante). Reimporte a lista/atualize o cadastro."))

    ano_letivo = int(turma_origem.ano_letivo or 2026)
    fechamento = FechamentoTrimestreTurma.query.filter_by(
        turma_id=turma_origem.id,
        ano_letivo=ano_letivo,
        trimestre=trimestre,
    ).first()
    if fechamento is None or fechamento.status != "fechado":
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Só é possível remanejar após fechar o trimestre selecionado."))

    snapshot = FechamentoTrimestreAluno.query.filter_by(
        turma_id=turma_origem.id,
        estudante_id=aluno.estudante_id,
        ano_letivo=ano_letivo,
        trimestre=trimestre,
    ).first()
    if snapshot is None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Snapshot do trimestre não encontrado. Feche o trimestre novamente."))

    already = Aluno.query.filter_by(turma_id=turma_destino.id, estudante_id=aluno.estudante_id, status="ativo").first()
    if already is not None:
        return redirect(url_for("pages.turma_detail", turma_id=turma_origem.id, tab="detalhes", trimestre=trimestre, error="Este aluno já está ativo na turma de destino."))

    snapshots_origem = (
        FechamentoTrimestreAluno.query.filter_by(
            turma_id=turma_origem.id,
            estudante_id=aluno.estudante_id,
            ano_letivo=ano_letivo,
        )
        .filter(FechamentoTrimestreAluno.trimestre <= trimestre)
        .all()
    )

    for s in snapshots_origem:
        existing_dest = FechamentoTrimestreAluno.query.filter_by(
            turma_id=turma_destino.id,
            estudante_id=aluno.estudante_id,
            ano_letivo=ano_letivo,
            trimestre=int(s.trimestre),
        ).first()
        if existing_dest is not None:
            # Snapshot is historical. If it already exists in the destination turma,
            # do not block the roster transfer (common when transferring a student back).
            # Keep existing record as-is.
            continue

        db.session.add(
            FechamentoTrimestreAluno(
                turma_id=turma_destino.id,
                estudante_id=aluno.estudante_id,
                origem_turma_id=turma_origem.id,
                ano_letivo=ano_letivo,
                trimestre=int(s.trimestre),
                media_final=s.media_final,
                total_pontos=s.total_pontos,
                avaliadas=int(s.avaliadas or 0),
                total_previstas=int(s.total_previstas or 0),
                locked=True,
                created_at=datetime.utcnow(),
            )
        )

    max_num = (
        db.session.query(func.max(Aluno.numero_chamada))
        .filter(Aluno.turma_id == turma_destino.id, Aluno.status == "ativo")
        .scalar()
    )
    if max_num is None:
        next_num = (Aluno.query.filter_by(turma_id=turma_destino.id, status="ativo").count() or 0) + 1
    else:
        next_num = int(max_num) + 1

    aluno.status = "transferido"

    db.session.add(
        Aluno(
            turma_id=turma_destino.id,
            estudante_id=aluno.estudante_id,
            nome_completo=aluno.nome_completo,
            numero_chamada=next_num,
            matricula=aluno.matricula,
            status="ativo",
            created_at=datetime.utcnow(),
        )
    )
    db.session.commit()

    return redirect(
        url_for(
            "pages.turma_detail",
            turma_id=turma_origem.id,
            tab="detalhes",
            trimestre=trimestre,
            transfer_ok="Aluno transferido com sucesso.",
        )
    )


@pages_bp.get("/configuracoes")
@login_required
def configuracoes():
    professor_id = int(current_user.id)
    selected = _selected_ano_letivo(professor_id=professor_id)

    years = {
        int(y)
        for (y,) in db.session.query(Turma.ano_letivo)
        .filter(Turma.professor_id == professor_id)
        .distinct()
        .all()
        if y is not None
    }
    years.update({selected, selected + 1})
    available_years = sorted(years)

    return render_template(
        "pages/configuracoes.html",
        selected_ano_letivo=selected,
        available_anos_letivos=available_years,
    )


@pages_bp.post("/configuracoes/ano-letivo")
@login_required
def configuracoes_set_ano_letivo():
    professor_id = int(current_user.id)
    year = _safe_int((request.form.get("ano_letivo") or "").strip(), 0)
    if year < 2000 or year > 2100:
        year = _selected_ano_letivo(professor_id=professor_id)

    session["ano_letivo"] = int(year)

    next_url = (request.form.get("next") or "").strip()
    if next_url.startswith("/"):
        return redirect(next_url)
    return redirect(url_for("pages.turmas"))


@pages_bp.get("/horario")
@login_required
def horario():
    professor_id = int(current_user.id)
    ano_letivo = _selected_ano_letivo(professor_id=professor_id)

    dias_cols = [(0, "SEG"), (1, "TER"), (2, "QUAR"), (3, "QUI"), (4, "SEX")]
    periods = ["Manhã", "Tarde", "Noite"]

    turma_rows = (
        db.session.query(TurmaHorario.dia_semana, TurmaHorario.hora, TurmaHorario.periodo, Turma.nome, Turma.id)
        .join(Turma, TurmaHorario.turma_id == Turma.id)
        .filter(Turma.professor_id == professor_id)
        .filter(Turma.ano_letivo == ano_letivo)
        .filter(TurmaHorario.dia_semana.in_([d for d, _ in dias_cols]))
        .order_by(TurmaHorario.periodo.asc(), TurmaHorario.hora.asc(), TurmaHorario.dia_semana.asc(), Turma.nome.asc())
        .all()
    )

    evento_rows = (
        db.session.query(
            HorarioEvento.dia_semana,
            HorarioEvento.hora,
            HorarioEvento.periodo,
            HorarioEvento.titulo,
            HorarioEvento.subtitulo,
            HorarioEvento.id,
        )
        .filter(HorarioEvento.professor_id == professor_id)
        .filter(HorarioEvento.dia_semana.in_([d for d, _ in dias_cols]))
        .order_by(HorarioEvento.periodo.asc(), HorarioEvento.hora.asc(), HorarioEvento.dia_semana.asc())
        .all()
    )

    grade: dict[str, dict[str, dict[int, list[dict]]]] = {p: {} for p in periods}
    for dia_semana, hora, periodo, nome, turma_id in turma_rows:
        if periodo not in grade:
            continue
        h = str(hora)
        d = int(dia_semana)
        parts = [p.strip() for p in (str(nome) or "").split(" - ")]
        base_nome = " - ".join(parts[:-1]).strip() if len(parts) >= 2 else str(nome)
        title = base_nome
        subtitle = ""
        if " - " in base_nome:
            first, rest = base_nome.split(" - ", 1)
            title = first.strip()
            subtitle = rest.strip()
        grade.setdefault(periodo, {}).setdefault(h, {}).setdefault(d, []).append(
            {"id": int(turma_id), "nome": nome, "display_title": title, "display_subtitle": subtitle}
        )

    for dia_semana, hora, periodo, titulo, subtitulo, evento_id in evento_rows:
        if periodo not in grade:
            continue
        h = str(hora)
        d = int(dia_semana)
        grade.setdefault(periodo, {}).setdefault(h, {}).setdefault(d, []).append(
            {
                "id": None,
                "evento_id": int(evento_id),
                "nome": str(titulo),
                "display_title": str(titulo),
                "display_subtitle": (str(subtitulo) if subtitulo else ""),
                "is_event": True,
            }
        )

    times_by_period: dict[str, list[str]] = {}
    for p in periods:
        times_by_period[p] = sorted(grade.get(p, {}).keys())

    return render_template(
        "pages/horario.html",
        selected_ano_letivo=ano_letivo,
        dias_cols=dias_cols,
        periods=periods,
        grade=grade,
        times_by_period=times_by_period,
    )


@pages_bp.post("/horario/eventos")
@login_required
def horario_evento_create():
    professor_id = int(current_user.id)

    periodo = (request.form.get("periodo") or "").strip()
    dia_raw = (request.form.get("dia_semana") or "").strip()
    hora = (request.form.get("hora") or "").strip()
    titulo = (request.form.get("titulo") or "HA").strip() or "HA"
    subtitulo = (request.form.get("subtitulo") or "Hora Atividade").strip() or None

    allowed_periodos = {"Manhã", "Tarde", "Noite"}
    if periodo not in allowed_periodos:
        return redirect(url_for("pages.horario"))

    try:
        dia = int(dia_raw)
    except ValueError:
        return redirect(url_for("pages.horario"))
    if dia not in set(range(0, 7)):
        return redirect(url_for("pages.horario"))

    if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", hora):
        return redirect(url_for("pages.horario"))

    existing = HorarioEvento.query.filter_by(
        professor_id=professor_id, dia_semana=dia, hora=hora, periodo=periodo
    ).first()
    if existing is None:
        db.session.add(
            HorarioEvento(
                professor_id=professor_id,
                dia_semana=dia,
                hora=hora,
                periodo=periodo,
                titulo=titulo,
                subtitulo=subtitulo,
            )
        )
        db.session.commit()

    return redirect(url_for("pages.horario"))


@pages_bp.post("/horario/eventos/<int:evento_id>/delete")
@login_required
def horario_evento_delete(evento_id: int):
    professor_id = int(current_user.id)
    evento = HorarioEvento.query.filter_by(id=evento_id, professor_id=professor_id).first()
    if evento is None:
        return redirect(url_for("pages.horario"))
    db.session.delete(evento)
    db.session.commit()
    return redirect(url_for("pages.horario"))


@pages_bp.get("/turmas/<int:turma_id>/diario")
@login_required
def turma_diario(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    hoje = date.today()

    dia_param = (request.args.get("dia") or "").strip()
    mes_param = (request.args.get("mes") or "").strip()

    dia_selecionado: date
    if dia_param:
        try:
            dia_selecionado = date.fromisoformat(dia_param)
        except ValueError:
            dia_selecionado = hoje
    else:
        dia_selecionado = hoje

    mes_ano: int
    mes_numero: int
    if mes_param:
        try:
            parts = mes_param.split("-")
            mes_ano = int(parts[0])
            mes_numero = int(parts[1])
            if not (1 <= mes_numero <= 12):
                raise ValueError
        except (ValueError, IndexError):
            mes_ano = dia_selecionado.year
            mes_numero = dia_selecionado.month
    else:
        mes_ano = dia_selecionado.year
        mes_numero = dia_selecionado.month

    primeiro_dia_mes = date(mes_ano, mes_numero, 1)
    ultimo_dia_num = calendar.monthrange(mes_ano, mes_numero)[1]
    ultimo_dia_mes = date(mes_ano, mes_numero, ultimo_dia_num)

    if dia_selecionado < primeiro_dia_mes or dia_selecionado > ultimo_dia_mes:
        dia_selecionado = primeiro_dia_mes

    anotacao_hoje = (
        DiarioAnotacao.query.filter_by(
            turma_id=turma.id,
            professor_id=int(current_user.id),
            data=hoje,
        )
        .order_by(DiarioAnotacao.updated_at.desc(), DiarioAnotacao.created_at.desc())
        .first()
    )

    anotacoes_dia_selecionado = (
        DiarioAnotacao.query.filter_by(
            turma_id=turma.id,
            professor_id=int(current_user.id),
            data=dia_selecionado,
        )
        .order_by(DiarioAnotacao.created_at.asc())
        .all()
    )

    # Marcações do calendário (dias com anotação) no mês corrente
    contagens_mes_rows = (
        db.session.query(DiarioAnotacao.data, func.count(DiarioAnotacao.id))
        .filter(
            DiarioAnotacao.turma_id == turma.id,
            DiarioAnotacao.professor_id == int(current_user.id),
            DiarioAnotacao.data >= primeiro_dia_mes,
            DiarioAnotacao.data <= ultimo_dia_mes,
        )
        .group_by(DiarioAnotacao.data)
        .all()
    )
    contagens_mes = {data_: int(qtd) for (data_, qtd) in contagens_mes_rows}

    prev_mes_ano = mes_ano
    prev_mes_num = mes_numero - 1
    if prev_mes_num < 1:
        prev_mes_num = 12
        prev_mes_ano -= 1
    next_mes_ano = mes_ano
    next_mes_num = mes_numero + 1
    if next_mes_num > 12:
        next_mes_num = 1
        next_mes_ano += 1

    prev_mes_str = f"{prev_mes_ano:04d}-{prev_mes_num:02d}"
    next_mes_str = f"{next_mes_ano:04d}-{next_mes_num:02d}"

    prev_mes_last_day = calendar.monthrange(prev_mes_ano, prev_mes_num)[1]
    prev_dia = date(prev_mes_ano, prev_mes_num, min(dia_selecionado.day, prev_mes_last_day))
    next_mes_last_day = calendar.monthrange(next_mes_ano, next_mes_num)[1]
    next_dia = date(next_mes_ano, next_mes_num, min(dia_selecionado.day, next_mes_last_day))

    cal = calendar.Calendar(firstweekday=0)  # segunda-feira
    cal_weeks = cal.monthdatescalendar(mes_ano, mes_numero)
    weekday_labels = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    mes_nomes = [
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    ]
    mes_label = f"{mes_nomes[mes_numero - 1].capitalize()} {mes_ano}"

    return render_template(
        "pages/diario.html",
        turma=turma,
        hoje=hoje,
        anotacao_hoje=anotacao_hoje,
        mes_atual_str=f"{mes_ano:04d}-{mes_numero:02d}",
        mes_ano=mes_ano,
        mes_numero=mes_numero,
        mes_label=mes_label,
        dia_selecionado=dia_selecionado,
        anotacoes_dia_selecionado=anotacoes_dia_selecionado,
        contagens_mes=contagens_mes,
        cal_weeks=cal_weeks,
        weekday_labels=weekday_labels,
        prev_mes_str=prev_mes_str,
        next_mes_str=next_mes_str,
        prev_dia_str=prev_dia.isoformat(),
        next_dia_str=next_dia.isoformat(),
    )


@pages_bp.post("/turmas/<int:turma_id>/diario/salvar")
@login_required
def turma_diario_salvar(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    anotacao_texto = (request.form.get("anotacao") or "").strip()
    titulo = (request.form.get("titulo") or "").strip() or None
    data_str = (request.form.get("data") or "").strip()
    anotacao_id = (request.form.get("anotacao_id") or "").strip()
    
    try:
        data_anotacao = date.fromisoformat(data_str) if data_str else date.today()
    except ValueError:
        data_anotacao = date.today()

    anotacao: DiarioAnotacao | None = None
    if anotacao_id:
        anotacao = (
            DiarioAnotacao.query.filter_by(
                id=int(anotacao_id),
                turma_id=turma.id,
                professor_id=int(current_user.id),
            )
            .first()
        )
    else:
        anotacao = (
            DiarioAnotacao.query.filter_by(
                turma_id=turma.id,
                professor_id=int(current_user.id),
                data=data_anotacao,
            )
            .order_by(DiarioAnotacao.updated_at.desc(), DiarioAnotacao.created_at.desc())
            .first()
        )

    if anotacao is not None:
        anotacao.titulo = titulo
        anotacao.anotacao = anotacao_texto
        anotacao.updated_at = datetime.utcnow()
    else:
        db.session.add(
            DiarioAnotacao(
                turma_id=turma.id,
                professor_id=int(current_user.id),
                data=data_anotacao,
                titulo=titulo,
                anotacao=anotacao_texto,
            )
        )

    db.session.commit()

    return redirect(url_for("pages.turma_diario", turma_id=turma.id))


@pages_bp.post("/turmas/<int:turma_id>/diario/excluir/<int:anotacao_id>")
@login_required
def turma_diario_excluir(turma_id: int, anotacao_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    anotacao = DiarioAnotacao.query.filter_by(
        id=anotacao_id,
        turma_id=turma.id,
        professor_id=int(current_user.id)
    ).first()

    if anotacao:
        db.session.delete(anotacao)
        db.session.commit()

    return redirect(url_for("pages.turma_diario", turma_id=turma.id))
