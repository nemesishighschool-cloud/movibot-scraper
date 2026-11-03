#!/usr/bin/env bash
# Publie la base SQLite compressée sur une branche ORPHELINE data-<source>.
# Un seul commit, forcé à chaque fois : l'historique ne grossit pas.
# Chaque source a SA branche → les 4 jobs matriciels ne se marchent pas dessus.
# Variables fournies par GitHub Actions : GITHUB_TOKEN, GITHUB_REPOSITORY.
# Usage : bash scripts/gh_checkpoint.sh frenchstream data/checkpoint.sqlite3
set -euo pipefail
SOURCE="${1:?source manquante}"
DB="${2:?base manquante}"
[ -f "$DB" ] || { echo "base absente : $DB"; exit 1; }
: "${GITHUB_TOKEN:?GITHUB_TOKEN manquant}"
: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY manquant}"
BRANCH="data-${SOURCE}"
URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

gzip -c "$DB" > "$TMP/index_web.sqlite3.gz"
TAILLE=$(stat -c%s "$TMP/index_web.sqlite3.gz")
if [ "$TAILLE" -gt 95000000 ]; then
    echo "⚠️ checkpoint ${TAILLE} octets : proche de la limite GitHub (100 Mo)"
fi

cd "$TMP"
git init -q
git checkout -q -b "$BRANCH"
git add index_web.sqlite3.gz
git -c user.name='movibot-bot' \
    -c user.email='movibot-bot@users.noreply.github.com' \
    commit -q -m "checkpoint ${SOURCE} $(date -u +%Y-%m-%dT%H:%M:%SZ)"
git remote add origin "$URL"
git push -q --force origin "$BRANCH"
echo "✅ ${BRANCH} publié (${TAILLE} octets gzip)"
