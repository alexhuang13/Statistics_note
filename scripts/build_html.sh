#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$ROOT_DIR/.web-build"
WORK_DIR="$BUILD_DIR/work"
RAW_DIR="$BUILD_DIR/raw"
SITE_DIR="$ROOT_DIR/_site"

rm -rf "$BUILD_DIR" "$SITE_DIR"
mkdir -p "$WORK_DIR" "$RAW_DIR" "$SITE_DIR"

cp "$ROOT_DIR"/*.tex "$ROOT_DIR"/*.bib "$ROOT_DIR"/*.sty "$WORK_DIR"/
cp -R "$ROOT_DIR/figures" "$WORK_DIR/figures"

# TeX4ht performs the semantic LaTeX-to-HTML conversion in an isolated
# directory. A second pass after BibTeX resolves citations and references.
(
  cd "$WORK_DIR"
  make4ht -u -f html5 -d "$RAW_DIR" main.tex 'mathjax,3'
  bibtex main
  make4ht -u -f html5 -d "$RAW_DIR" main.tex 'mathjax,3'
)

python3 "$ROOT_DIR/scripts/postprocess_html.py" "$RAW_DIR" "$SITE_DIR"
