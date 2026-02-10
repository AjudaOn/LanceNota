#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# shellcheck disable=SC1091
. "$project_dir/.venv/bin/activate"

export FLASK_APP="lancenotas:create_app"
export FLASK_ENV="${FLASK_ENV:-development}"

python "$project_dir/run.py"

