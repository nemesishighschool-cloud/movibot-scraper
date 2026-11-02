import os

from scraper.frontier import maintenant
from scraper.storage import (ajouter_frontiere, echec, enregistrer, ouvrir,
                             stats, suivants)


def item(n, statut="pending"):
    return {"canonical_path": f"/film-{n}.html", "source": "frenchstream",
            "url": f"https://fs26.lol/film-{n}.html", "lastmod": None,
            "first_seen": maintenant(), "status": statut}


def media(n):
    return {"source": "frenchstream", "source_domain": "fs26.lol",
            "canonical_path": f"/film-{n}.html",
            "page_url": f"https://fs26.lol/film-{n}.html",
            "title": f"Film {n}", "kind": "film", "year": 2020,
            "embed_url": f"https://vidzy.org/embed-abc{n}.html",
            "download_url": f"https://vidzy.org/d/abc{n}.html",
            "etat_lecteur": "pret", "status": "ok",
            "first_seen": maintenant(), "last_checked": maintenant()}


def test_reprise_sans_doublon(tmp_path):
    db = str(tmp_path / "test.sqlite3")
    c = ouvrir(db)
    ajouter_frontiere(c, [item(i) for i in range(5)])
    assert len(suivants(c)) == 5
    enregistrer(c, media(0))
    enregistrer(c, media(0))                    # rejoué → pas de doublon
    assert stats(c)["fiches"] == 1
    assert stats(c)["doublons"] == 0
    assert len(suivants(c)) == 4
    assert stats(c)["avec_lecteur"] == 1
    c.close()


def test_incremental_lastmod():
    # Vérifie la logique sans réseau : une fiche faite n'est rouverte que si lastmod change.
    import sqlite3
    c = sqlite3.connect(":memory:")
    from scraper.storage import SCHEMA
    c.executescript(SCHEMA)
    a = item(1)
    ajouter_frontiere(c, [a])
    c.execute("UPDATE frontier SET status='done', lastmod='2026-01-01' WHERE canonical_path=?",
              (a["canonical_path"],))
    c.commit()
    a2 = dict(a, lastmod="2026-11-02")
    n = ajouter_frontiere(c, [a2], incremental=True)
    etat = c.execute("SELECT status FROM frontier WHERE canonical_path=?",
                     (a["canonical_path"],)).fetchone()[0]
    assert n == 1 and etat == "pending"
    # Sans changement de lastmod, rien ne rouvre.
    ajouter_frontiere(c, [a2], incremental=True)
    etat = c.execute("SELECT status FROM frontier WHERE canonical_path=?",
                     (a["canonical_path"],)).fetchone()[0]
    assert etat == "pending"       # déjà remis en attente, pas écrasé
    c.close()


def test_echec_apres_3_essais():
    import sqlite3
    c = sqlite3.connect(":memory:")
    from scraper.storage import SCHEMA
    c.executescript(SCHEMA)
    ajouter_frontiere(c, [item(9)])
    for _ in range(3):
        echec(c, "/film-9.html", "timeout")
    etat = c.execute("SELECT status, tries FROM frontier WHERE canonical_path='/film-9.html'"
                     ).fetchone()
    assert etat[0] == "error" and etat[1] == 3
    c.close()
