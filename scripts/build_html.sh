#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$ROOT_DIR/.web-build/raw"
SITE_DIR="$ROOT_DIR/_site"

"$ROOT_DIR/scripts/convert_tex4ht.sh"
rm -rf "$SITE_DIR"
mkdir -p "$SITE_DIR"
python3 "$ROOT_DIR/scripts/postprocess_html.py" "$RAW_DIR" "$SITE_DIR"
