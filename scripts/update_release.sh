#!/bin/sh
set -eu

# Rebuilds the local `_release/` folder with only the deployable backend code.
# This folder is optional and is meant for workflows that keep production pointing
# to `_release/` while the repo root may contain extra files (e.g. Designer/).

ROOT_DIR="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
DEST_DIR="$ROOT_DIR/_release"

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

cd "$ROOT_DIR"

git ls-files | while IFS= read -r file; do
  case "$file" in
    lancenotas/*|migrations/*|scripts/*|requirements.txt|run.py|.env.example|README.md|Atualizar_git_any.txt)
      parent_dir="$(dirname "$file")"
      mkdir -p "$DEST_DIR/$parent_dir"
      cp -p "$file" "$DEST_DIR/$file"
      ;;
  esac
done

printf "%s\n" "OK: release atualizado em $DEST_DIR"

