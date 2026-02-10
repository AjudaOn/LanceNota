#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if [ ! -d "$project_dir/.venv" ]; then
  echo "Missing .venv. Create it with: python3 -m venv .venv" >&2
  exit 1
fi

# shellcheck disable=SC1091
. "$project_dir/.venv/bin/activate"

echo "Activated venv: $VIRTUAL_ENV"

