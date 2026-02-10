from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from pypdf import PdfReader


@dataclass(frozen=True)
class ImportedStudent:
    nome: str
    numero_chamada: int | None


@dataclass(frozen=True)
class ImportedTurmaInfo:
    serie: str | None
    turma_letra: str | None
    periodo: str | None
    disciplina: str | None
    ano_letivo: int | None


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_resumo_registro_classe(pdf_path: str) -> tuple[ImportedTurmaInfo, list[ImportedStudent]]:
    reader = PdfReader(pdf_path)
    text_parts: list[str] = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")

    text = "\n".join(text_parts)
    text = text.replace("\u0000", "")

    serie_match = re.search(r"SERIAÇÃO:\s*([^\n]+)", text, flags=re.IGNORECASE)
    serie_raw = _clean_spaces(serie_match.group(1)) if serie_match else None
    serie: str | None = None
    if serie_raw:
        m = re.search(r"(\d+)\s*º?\s*Ano", serie_raw, flags=re.IGNORECASE)
        if m:
            serie = f"{int(m.group(1))}º"

    ano_letivo_match = re.search(r"ANO LETIVO:\s*([0-9]{4})", text, flags=re.IGNORECASE)
    ano_letivo = int(ano_letivo_match.group(1)) if ano_letivo_match else None

    turma_match = re.search(r"TURMA:\s*([A-H])\b", text, flags=re.IGNORECASE)
    turma_letra = turma_match.group(1).upper() if turma_match else None

    # Periodo costuma aparecer como uma linha sozinha: Manhã/Tarde/Noite
    periodo_match = re.search(r"\n(Manhã|Tarde|Noite)\n", text, flags=re.IGNORECASE)
    periodo = periodo_match.group(1).capitalize() if periodo_match else None

    # Disciplina: no exemplo vem como "ARTE" em uma linha isolada perto do topo
    disciplina = None
    if "RESUMO DO REGISTRO DE CLASSE" in text:
        after = text.split("RESUMO DO REGISTRO DE CLASSE", 1)[1]
        lines = [ln.strip() for ln in after.splitlines() if ln.strip()]
        for ln in lines[:10]:
            if re.fullmatch(r"[A-ZÇÃÕÁÉÍÓÚÜ ]{3,}", ln) and "TURMA:" not in ln:
                disciplina = _clean_spaces(ln.title())
                break

    # Students: linhas com "NOME ... <num> <mov> <saldo>"
    students: list[ImportedStudent] = []
    for line in _iter_student_lines(text.splitlines()):
        parsed = _parse_student_line(line)
        if parsed:
            students.append(parsed)

    info = ImportedTurmaInfo(
        serie=serie,
        turma_letra=turma_letra,
        periodo=periodo,
        disciplina=disciplina,
        ano_letivo=ano_letivo,
    )
    return info, students


def _iter_student_lines(lines: Iterable[str]) -> Iterable[str]:
    started = False
    for raw in lines:
        line = _clean_spaces(raw)
        if not line:
            continue
        if "NOME DO ALUNO" in line.upper():
            started = True
            continue
        if not started:
            continue
        if line.startswith("¹") or line.startswith("²") or "Impresso por" in line:
            break
        yield line


def _parse_student_line(line: str) -> ImportedStudent | None:
    # Ex: "ADRIEL MANGOLI NAVARRO 1 0 -18"
    m = re.match(r"^(?P<name>.+?)\s+(?P<num>\d{1,3})\s+\d+\s+-?\d+\s*$", line)
    if not m:
        return None
    name = _clean_spaces(m.group("name")).title()
    try:
        numero = int(m.group("num"))
    except ValueError:
        numero = None
    return ImportedStudent(nome=name, numero_chamada=numero)

