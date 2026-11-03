"""Stockage SQLite : base, file d'attente, reprise. Aucun média stocké."""

from __future__ import annotations

import json
import os
import sqlite3

from .frontier import maintenant

SCHEMA = """
CREATE TABLE IF NOT EXISTS web_media (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL, source_domain TEXT, canonical_path TEXT NOT NULL UNIQUE,
  page_url TEXT, title TEXT, kind TEXT, year INTEGER, season INTEGER,
  episode_count INTEGER, languages TEXT, genres TEXT, duration_min INTEGER,
  synopsis TEXT, poster_url TEXT, players TEXT, embed_url TEXT,
  download_url TEXT, etat_lecteur TEXT, lastmod TEXT, first_seen TEXT,
  last_checked TEXT, status TEXT, error TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS frontier (
  canonical_path TEXT PRIMARY KEY, source TEXT, url TEXT, lastmod TEXT,
  first_seen TEXT, status TEXT DEFAULT 'pending', tries INTEGER DEFAULT 0,
  error TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS progress (
  source TEXT PRIMARY KEY, done INTEGER, total INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT, ended_at TEXT,
  inserted INTEGER, errors INTEGER, note TEXT
);
CREATE INDEX IF NOT EXISTS idx_frontier_status ON frontier(status, source);
CREATE INDEX IF NOT EXISTS idx_media_source ON web_media(source, kind);
"""

COLONNES = ["source", "source_domain", "canonical_path", "page_url", "title", "kind",
            "year", "season", "episode_count", "languages", "genres", "duration_min",
            "synopsis", "poster_url", "players", "embed_url", "download_url",
            "etat_lecteur", "lastmod", "first_seen", "last_checked", "status",
            "error", "notes"]


def ouvrir(chemin: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(chemin) or ".", exist_ok=True)
    # WAL + busy_timeout : plusieurs workers (un par source) écrivent en même temps.
    c = sqlite3.connect(chemin, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.executescript(SCHEMA)
    cols = {r[1] for r in c.execute("PRAGMA table_info(web_media)")}
    for col, typ in [("etat_lecteur", "TEXT")]:
        if col not in cols:
            c.execute(f"ALTER TABLE web_media ADD COLUMN {col} {typ}")
    c.commit()
    return c


def ajouter_frontiere(c: sqlite3.Connection, items: list[dict],
                      incremental: bool = True) -> int:
    """N'écrase jamais une fiche déjà faite ; met à jour lastmod si plus récent."""
    n = 0
    for it in items:
        row = c.execute("SELECT status, lastmod FROM frontier WHERE canonical_path=?",
                        (it["canonical_path"],)).fetchone()
        if row and row[0] == "done" and incremental:
            if it.get("lastmod") and it["lastmod"] != row[1]:
                c.execute("UPDATE frontier SET status='pending', lastmod=?, updated_at=? "
                          "WHERE canonical_path=?",
                          (it["lastmod"], maintenant(), it["canonical_path"]))
                n += 1
            continue
        c.execute("INSERT OR REPLACE INTO frontier "
                  "(canonical_path, source, url, lastmod, first_seen, status, updated_at) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (it["canonical_path"], it["source"], it["url"], it.get("lastmod"),
                   it.get("first_seen") or maintenant(), "pending", maintenant()))
        n += 1
    c.commit()
    return n


def suivants(c: sqlite3.Connection, source: str | None = None,
             limite: int | None = None) -> list[dict]:
    sql = "SELECT * FROM frontier WHERE status='pending'"
    args: list = []
    if source:
        sql += " AND source=?"
        args.append(source)
    sql += " ORDER BY canonical_path"
    if limite:
        sql += " LIMIT ?"
        args.append(limite)
    c.row_factory = sqlite3.Row
    return [dict(r) for r in c.execute(sql, args)]


def enregistrer(c: sqlite3.Connection, d: dict) -> None:
    d.setdefault("last_checked", maintenant())
    d.setdefault("first_seen", maintenant())
    c.execute("INSERT OR REPLACE INTO web_media (" + ",".join(COLONNES) + ") VALUES (" +
              ",".join("?" for _ in COLONNES) + ")", [d.get(k) for k in COLONNES])
    c.execute("UPDATE frontier SET status=?, error=NULL, updated_at=? "
              "WHERE canonical_path=?", ("done", maintenant(), d["canonical_path"]))
    c.commit()


def echec(c: sqlite3.Connection, chemin: str, message: str) -> None:
    c.execute("UPDATE frontier SET status='pending', tries=tries+1, error=?, "
              "updated_at=? WHERE canonical_path=? AND tries < 3",
              (message[:200], maintenant(), chemin))
    c.execute("UPDATE frontier SET status='error' WHERE canonical_path=? AND tries >= 3",
              (chemin,))
    c.commit()


def stats(c: sqlite3.Connection) -> dict:
    un = lambda sql: c.execute(sql).fetchone()[0]
    return {
        "fiches": un("SELECT COUNT(*) FROM web_media"),
        "doublons": un("SELECT COUNT(*) FROM web_media") -
                    un("SELECT COUNT(DISTINCT canonical_path) FROM web_media"),
        "en_attente": un("SELECT COUNT(*) FROM frontier WHERE status='pending'"),
        "erreurs": un("SELECT COUNT(*) FROM frontier WHERE status='error'"),
        "terminees": un("SELECT COUNT(*) FROM frontier WHERE status='done'"),
        "avec_lecteur": un("SELECT COUNT(*) FROM web_media WHERE embed_url IS NOT NULL"),
        "lecteurs_prets": un("SELECT COUNT(*) FROM web_media WHERE etat_lecteur='pret'"),
        "par_source": dict(c.execute("SELECT source, COUNT(*) FROM web_media GROUP BY source")),
        "par_statut": dict(c.execute("SELECT status, COUNT(*) FROM web_media GROUP BY status")),
    }
