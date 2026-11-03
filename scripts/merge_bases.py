#!/usr/bin/env python3
"""Fusionne les 4 bases par source en une seule, puis exporte CSV/XLSX.

Usage : python3 scripts/merge_bases.py data/src-*.sqlite3 \
            --out data/index_web_complete.sqlite3 --exports exports/
"""

from __future__ import annotations

import argparse
import glob
import os
import sqlite3

from scraper.export import exporter
from scraper.storage import COLONNES, ouvrir


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bases", nargs="+", help="bases SQLite par source")
    p.add_argument("--out", default="data/index_web_complete.sqlite3")
    p.add_argument("--exports", default="exports")
    a = p.parse_args()

    chemins = []
    for motif in a.bases:
        chemins.extend(glob.glob(motif))
    chemins = [c for c in dict.fromkeys(chemins) if os.path.exists(c)]
    if not chemins:
        raise SystemExit("Aucune base à fusionner")

    out = ouvrir(a.out)
    total = 0
    for chemin in chemins:
        try:
            out.execute("ATTACH DATABASE ? AS src", (chemin,))
            n = out.execute("SELECT COUNT(*) FROM src.web_media").fetchone()[0]
            out.execute("INSERT OR REPLACE INTO main.web_media (" + ",".join(COLONNES) +
                        ") SELECT " + ",".join(COLONNES) + " FROM src.web_media")
            out.execute("DETACH DATABASE src")
            total += n
            print(f"  {os.path.basename(chemin):38} → {n:6} lignes", flush=True)
        except Exception as e:
            print(f"  ✗ {chemin} : {type(e).__name__}: {str(e)[:100]}")
            try:
                out.execute("DETACH DATABASE src")
            except Exception:
                pass
    out.commit()
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
