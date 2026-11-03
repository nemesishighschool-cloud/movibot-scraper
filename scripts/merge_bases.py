#!/usr/bin/env python3
"""Fusionne les bases par source en une seule, puis exporte CSV/XLSX.

Usage : python3 scripts/merge_bases.py 'data/src-*.sqlite3' \
            --out data/index_web_complete.sqlite3 --exports exports/

Copie ligne à ligne (pas de ATTACH : les bases sont en WAL et ATTACH échoue
quand un journal est présent). Les colonnes absentes d'une base ancienne sont
ignorées proprement.
"""

from __future__ import annotations

import argparse
import glob
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.export import exporter
from scraper.storage import COLONNES, ouvrir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bases", nargs="+", help="motifs de bases SQLite par source")
    p.add_argument("--out", default="data/index_web_complete.sqlite3")
    p.add_argument("--exports", default="exports")
    a = p.parse_args()

    chemins = []
    for motif in a.bases:
        chemins.extend(glob.glob(motif))
    chemins = [c for c in dict.fromkeys(chemins) if os.path.exists(c)]
    if not chemins:
        print("ℹ️ Aucune base publiée : export vide (le workflow reste vert)")

    out = ouvrir(a.out)
    for chemin in chemins:
        try:
            src = sqlite3.connect(f"file:{chemin}?mode=ro", uri=True)
            cols_src = {r[1] for r in src.execute("PRAGMA table_info(web_media)")}
            communes = [c for c in COLONNES if c in cols_src]
            if "canonical_path" not in communes:
                print(f"  ✗ {chemin} : pas de colonne canonical_path")
                src.close()
                continue
            rows = src.execute("SELECT " + ",".join(communes) + " FROM web_media").fetchall()
            sql = ("INSERT OR REPLACE INTO web_media (" + ",".join(communes) +
                   ") VALUES (" + ",".join("?" for _ in communes) + ")")
            out.executemany(sql, rows)
            out.commit()
            print(f"  {os.path.basename(chemin):38} → {len(rows):6} lignes", flush=True)
            src.close()
        except Exception as e:
            print(f"  ✗ {chemin} : {type(e).__name__}: {str(e)[:100]}")

    final = out.execute("SELECT COUNT(*) FROM web_media").fetchone()[0]
    doublons = final - out.execute(
        "SELECT COUNT(DISTINCT canonical_path) FROM web_media").fetchone()[0]
    par = dict(out.execute("SELECT source, COUNT(*) FROM web_media GROUP BY source"))
    out.close()

    res = exporter(a.out, a.exports)
    print(f"  TOTAL {final} lignes (doublons {doublons}) | par source {par}")
    print(f"  CSV  {res['csv']}")
    print(f"  XLSX {res['xlsx']}")


if __name__ == "__main__":
    main()
