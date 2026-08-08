#!/usr/bin/env bash
# Cyber Site — rebuild + deploy to GitHub Pages (docs/ on main)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "▶ Rebuilding site…"
PY=~/.hermes/hermes-agent/venv/bin/python3
"$PY" scripts/build_site.py --fresh

echo "▶ Committing…"
git add -A
git commit -m "Build site $(date '+%Y-%m-%d %H:%M')" || echo "(nothing to commit)"

echo "▶ Pushing to origin/main…"
git push origin main

echo "✅ Deployed. Give GitHub Pages ~1 min, then check the Pages URL."
