"""Estimation de durée à partir des catalogues RÉELLEMENT mesurés.

Temps unitaires mesurés :
  - FrenchStream avec clics sur 3 onglets : ~5,5 s de travail par fiche
  - sources en HTTP simple (Coflix, Wawacity, FRAnime) : ~0,8 s
On ajoute la pause par source (jamais en dessous du Crawl-delay du robots.txt)
et le temps de construction de la frontière, qui s'exécute AVANT les workers.
Le GPU n'intervient dans aucun de ces chiffres.
"""

from __future__ import annotations

from .config import Settings, SOURCES, actives

# Surcoût mesuré par fiche, hors pause (chargement + parsing + clics + écriture)
SURCOUT = {"frenchstream": 5.5, "franime": 0.8, "coflix": 0.8,
           "wawacity": 0.8, "monstream": 3.0, "flemmix": 3.0, "darkiworld": 0.8}

# Frontière : sitemap 8,9 Mo, index de 532 sitemaps, 8 309 pages de listing Wawacity.
FRONTIERE = {"frenchstream": 12, "franime": 3, "coflix": 90,
             "wawacity": 9000, "monstream": 5, "flemmix": 5, "darkiworld": 5}

# Trafic réseau approximatif par fiche (HTML rendu, images bloquées)
KO_PAR_FICHE = {"frenchstream": 210, "franime": 70, "coflix": 300,
                "wawacity": 60, "monstream": 100, "flemmix": 100, "darkiworld": 60}


def estimer(s: Settings | None = None) -> dict:
    s = s or Settings()
    lignes = []
    for n in actives():
        c = SOURCES[n]
        if s.source and n != s.source:
            continue
        fiches = c["mesure"]
        if not fiches:
            continue
        base = s.pause if s.pause != 3.0 else c.get("pause", s.pause)
        # Le Crawl-delay du robots.txt est impératif, même si la pause est plus courte.
        pause = max(base, c.get("crawl_delay", 0) or 0)
        surcout = min(SURCOUT.get(n, 1.0), 1.5) if not s.joueurs else SURCOUT.get(n, 1.0)
        front = FRONTIERE.get(n, 0)
        secondes = fiches * (pause + surcout) + front
        lignes.append({"source": n, "fiches_mesurees": fiches,
                       "pause_s": pause, "surcout_s": surcout,
                       "frontiere_s": front,
                       "secondes": round(secondes),
                       "heures": round(secondes / 3600, 1),
                       "jours": round(secondes / 86400, 2),
                       "trafic_go": round(fiches * KO_PAR_FICHE.get(n, 100) / 1048576, 1)})
    total_seq = sum(x["secondes"] for x in lignes)
    frontiere_totale = sum(x["frontiere_s"] for x in lignes)
    mur_travail = max((x["secondes"] - x["frontiere_s"] for x in lignes), default=0)
    mur = frontiere_totale + mur_travail          # la frontière est faite avant les workers
    goulot = max(lignes, key=lambda x: x["secondes"])["source"] if lignes else None
    nb_sources = len(lignes)
    workers = s.workers if s.workers > 0 else nb_sources
    return {
        "sources_actives": nb_sources,
        "total_fiches": sum(x["fiches_mesurees"] for x in lignes),
        "trafic_total_go": round(sum(x["trafic_go"] for x in lignes), 1),
        "par_source": lignes,
        "frontiere_avant_workers": {"secondes": frontiere_totale,
                                    "heures": round(frontiere_totale / 3600, 2)},
        "sequentiel_1_worker": {"heures": round(total_seq / 3600, 1),
                                "jours": round(total_seq / 86400, 2)},
        "parallele_1_worker_par_source": {
            "workers": workers,
            "heures": round(mur / 3600, 1),
            "jours": round(mur / 86400, 2),
            "goulot": goulot,
            "gain": round(total_seq / mur, 1) if mur else 0},
        "avec_no_players": {
            "heures": round((frontiere_totale + max(
                (x["fiches_mesurees"] * (x["pause_s"] + min(x["surcout_s"], 1.5))
                 for x in lignes), default=0)) / 3600, 1)},
        "sessions_colab_12h_necessaires": max(1, -(-int(mur / 3600) // 12)) if mur else 0,
        "gpu": "aucun effet : Chrome, le parsing HTML et le réseau sont CPU/RAM/bande passante, pas GPU",
        "hypotheses": "catalogues mesurés le 2026-11-02 ; machine allumée en continu ; hors pannes et changement de domaine",
    }
