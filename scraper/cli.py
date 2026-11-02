"""Interface en ligne de commande.

    python3 -m scraper.cli init
    python3 -m scraper.cli sync
    python3 -m scraper.cli run --limit 200
    python3 -m scraper.cli status
    python3 -m scraper.cli export
    python3 -m scraper.cli verify
    python3 -m scraper.cli probe
    python3 -m scraper.cli preview
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .config import Settings
from .daemon import executer, preparer
from .export import exporter
from .players import sonde
from .storage import ouvrir, stats


def main(argv=None):
    p = argparse.ArgumentParser(prog="movibot-scraper",
                                description="Moteur d'indexation web MoviBot")
    sub = p.add_subparsers(dest="cmd", required=True)
    for nom in ["init", "sync", "status", "verify", "probe", "export", "preview"]:
        sub.add_parser(nom)
    r = sub.add_parser("run")
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--source", choices=["frenchstream", "franime"], default=None)
    r.add_argument("--pause", type=float, default=None)
    r.add_argument("--no-players", action="store_true")
    r.add_argument("--probe-players", action="store_true")
    a = p.parse_args(argv)
    s = Settings()
    if a.cmd == "run":
        if a.limit:
            s.limite = a.limit
        if a.source:
            s.source = a.source
        if a.pause is not None:
            s.pause = a.pause
        if a.no_players:
            s.joueurs = False
        if a.probe_players:
            s.sonder = True
    if a.cmd == "run":
        print(json.dumps(executer(s), ensure_ascii=False, indent=2))
        return 0

    c = ouvrir(s.db)
    if a.cmd == "init":
        print(json.dumps({"ok": True, "base": s.db, **stats(c)},
                         ensure_ascii=False, indent=2))
    elif a.cmd == "sync":
        preparer(c, s)
        print(json.dumps({"ok": True, "base": s.db, **stats(c)},
                         ensure_ascii=False, indent=2))
    elif a.cmd == "status":
        print(json.dumps(stats(c), ensure_ascii=False, indent=2))
    elif a.cmd == "verify":
        st = stats(c)
        problemes = []
        if st["doublons"]:
            problemes.append(f"{st['doublons']} doublons")
        if st["fiches"] == 0:
            problemes.append("base vide")
        rows = c.execute("SELECT COUNT(*) FROM web_media WHERE title IS NULL OR title=''").fetchone()[0]
        if rows:
            problemes.append(f"{rows} fiches sans titre")
        print(json.dumps({"ok": not problemes, "controles": {
            "lignes": st["fiches"], "doublons": st["doublons"],
            "sans_titre": rows, "avec_lecteur": st["avec_lecteur"]},
            "problemes": problemes}, ensure_ascii=False, indent=2))
        return 0 if not problemes else 1
    elif a.cmd == "export":
        print(json.dumps(exporter(s.db), ensure_ascii=False, indent=2))
    elif a.cmd == "probe":
        urls = [r[0] for r in c.execute(
            "SELECT DISTINCT embed_url FROM web_media WHERE embed_url IS NOT NULL")]
        bilan = {}
        for u in urls:
            etat = sonde(u)["etat"]
            bilan[etat] = bilan.get(etat, 0) + 1
            c.execute("UPDATE web_media SET etat_lecteur=? WHERE embed_url=?", (etat, u))
        c.commit()
        print(json.dumps({"testes": len(urls), "etats": bilan},
                         ensure_ascii=False, indent=2))
    elif a.cmd == "preview":
        from .preview import demarrer
        demarrer(s.db)
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
