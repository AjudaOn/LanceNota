from __future__ import annotations

import re
import unicodedata
from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy import or_

from ..extensions import db
from ..models import (
    Aluno,
    Atividade,
    AtividadeAula,
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

    turmas = Turma.query.filter_by(professor_id=professor_id).all()
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
                ),
                400,
            )

        allowed_series = {"5º", "6º", "7º", "8º", "9º", "1º Ano", "2º Ano"}
        allowed_turmas = set("ABCDEFGH")
        allowed_periodos = {"Manhã", "Tarde", "Noite"}

        if serie not in allowed_series:
            return render_template("pages/turmas.html", error="Série inválida."), 400
        if turma_letra not in allowed_turmas:
            return render_template("pages/turmas.html", error="Turma inválida."), 400

        try:
            ano_letivo = int(ano_letivo_raw) if ano_letivo_raw else 2026
        except ValueError:
            return render_template("pages/turmas.html", error="Ano letivo inválido."), 400

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
                return render_template("pages/turmas.html", error="Turma não encontrada."), 404

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

    turmas_db = Turma.query.filter_by(professor_id=int(current_user.id)).all()

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
        alunos_count = Aluno.query.filter_by(turma_id=t.id).count()
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

    return render_template("pages/turmas.html", turmas=turma_cards, q=q)


@pages_bp.get("/turmas/<int:turma_id>")
@login_required
def turma_detail(turma_id: int):
    turma = Turma.query.filter_by(id=turma_id, professor_id=int(current_user.id)).first()
    if turma is None:
        return redirect(url_for("pages.turmas"))

    today = date.today()

    tab = (request.args.get("tab") or "detalhes").strip().lower()
    if tab not in {"detalhes", "atividades"}:
        tab = "detalhes"

    trimestre = request.args.get("trimestre", "1")
    try:
        current_trimestre = max(1, min(4, int(trimestre)))
    except ValueError:
        current_trimestre = 1

    alunos_count = Aluno.query.filter_by(turma_id=turma.id).count()
    atividades_count = Atividade.query.filter_by(turma_id=turma.id).count()
    alunos = (
        Aluno.query.filter_by(turma_id=turma.id)
        .order_by(Aluno.numero_chamada.asc(), Aluno.nome_completo.asc())
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
        if all_atividades:
            atividade_ids = [a.id for a in all_atividades]
            aulas = AtividadeAula.query.filter(AtividadeAula.atividade_id.in_(atividade_ids)).all()
            eligible_aulas = [a for a in aulas if a.data is None or a.data <= today]
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

            atividades_by_trimestre: dict[int, list[Atividade]] = {1: [], 2: [], 3: [], 4: []}
            for a in all_atividades:
                tri = int(a.trimestre or 1)
                tri = max(1, min(4, tri))
                atividades_by_trimestre[tri].append(a)

            for aluno in alunos:
                aluno_row: dict[str, float | None] = {}
                total_sum = 0.0
                total_peso = 0.0

                for tri in (1, 2, 3, 4):
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
                    aluno_row[f"t{tri}"] = round(tri_sum / tri_peso, 2) if tri_peso > 0 else None
                    if tri_peso > 0:
                        total_sum += tri_sum
                        total_peso += tri_peso

                aluno_row["total"] = round(total_sum / total_peso, 2) if total_peso > 0 else None
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

            eligible_aulas_for_media = [a for a in selected_aulas if a.data is None or a.data <= today]
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
        imported=request.args.get("imported"),
        import_status=request.args.get("import_status"),
        import_mismatch=(request.args.get("import_mismatch") or "").strip(),
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

    trimestre = max(1, min(4, _safe_int(request.form.get("trimestre"), 1)))
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

    trimestre = max(1, min(4, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
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

    trimestre = max(1, min(4, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
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

    trimestre = max(1, min(4, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
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

    trimestre = max(1, min(4, _safe_int(request.form.get("trimestre"), atividade.trimestre or 1)))
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
        aluno = Aluno(
            turma_id=turma_id,
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
    return render_template("pages/fechamento.html")


@pages_bp.get("/configuracoes")
@login_required
def configuracoes():
    return render_template("pages/configuracoes.html")


@pages_bp.get("/horario")
@login_required
def horario():
    professor_id = int(current_user.id)

    dias_cols = [(0, "SEG"), (1, "TER"), (2, "QUAR"), (3, "QUI"), (4, "SEX")]
    periods = ["Manhã", "Tarde", "Noite"]

    turma_rows = (
        db.session.query(TurmaHorario.dia_semana, TurmaHorario.hora, TurmaHorario.periodo, Turma.nome, Turma.id)
        .join(Turma, TurmaHorario.turma_id == Turma.id)
        .filter(Turma.professor_id == professor_id)
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
