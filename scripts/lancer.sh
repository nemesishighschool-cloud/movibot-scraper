#!/usr/bin/env bash
# Raccourci : lance l'indexation complète en tâche de fond avec reprise.
set -e
cd "$(dirname "$0")/.."
mkdir -p data
[ -x .venv/bin/python ] || { echo "Lance d'abord l'installation du README"; exit 1; }
PAUSE="${PAUSE:-4}"
echo "=== MoviBot Scraper — pause ${PAUSE}s ==="
nohup .venv/bin/python -m scraper.cli run --pause "$PAUSE" >> data/scraper.log 2>&1 &
echo "PID $! | suivi : tail -f data/scraper.log"
echo "Reprise automatique : relance simplement ce script."
