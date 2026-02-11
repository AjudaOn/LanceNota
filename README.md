# LanceNotas

Sistema web (Flask + SQLite) para gestão de turmas e lançamentos de notas/observações.

## Requisitos

- Python 3.x

## Setup (desenvolvimento)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Banco de dados / migrations

```bash
export FLASK_APP="lancenotas:create_app"
flask db upgrade
```

## Rodar o servidor

```bash
./scripts/dev.sh
```

## Observações

- Arquivos locais como `.venv/` e `instance/` (incluindo o SQLite) ficam fora do versionamento.
- O sistema considera **3 trimestres** (ajuste em `lancenotas/constants.py`).
