#!/usr/bin/env bash
# Restaure le checkpoint d'une source depuis sa branche data-<source>.
# Usage : bash scripts/gh_restore.sh frenchstream data/index_web.sqlite3
set -uo pipefail
SOURCE="${1:?source manquante}"
OUT="${2:-data/index_web.sqlite3}"
BRANCH="data-${SOURCE}"
mkdir -p "$(dirname "$OUT")"

# En CI, actions/checkout crée origin. En local, on le recrée au besoin.
if ! git remote get-url origin >/dev/null 2>&1; then
    if [ -n "${GITHUB_REPOSITORY:-}" ]; then
        URL="https://github.com/${GITHUB_REPOSITORY}.git"
        if [ -n "${GITHUB_TOKEN:-}" ]; then
            URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
        fi
        git remote add origin "$URL" 2>/dev/null || true
    fi
fi

if git fetch -q origin "${BRANCH}" 2>/dev/null && \
   git cat-file -e "FETCH_HEAD:index_web.sqlite3.gz" 2>/dev/null; then
    git show "FETCH_HEAD:index_web.sqlite3.gz" | gunzip -c > "$OUT"
    echo "✅ checkpoint restauré depuis ${BRANCH} ($(du -h "$OUT" | cut -f1))"
else
    echo "ℹ️ aucun checkpoint ${BRANCH} → nouvelle base"
fi
