"""Estimation de durée à partir des catalogues RÉELLEMENT mesurés.

Les temps unitaires viennent des exécutions réelles :
  - FrenchStream avec clics sur 3 onglets : ~5,5 s de travail par fiche
  - sources en HTTP simple (Coflix, Wawacity, FRAnime) : ~0,8 s
On ajoute la pause par source. Le GPU n'intervient dans aucun de ces chiffres.
"""

from __future__ import annotations

from .config import Settings, SOURCES, actives

# Surcoût mesuré par fiche, hors pause (chargement + parsing + clics + écriture)
SURCOUT = {
    "frenchstream": 5.5,     # navigateur + 3 onglets de lecteurs
    "franime": 0.8,
    "coflix": 0.8,
    "wawacity": 0.8,
    "monstream": 3.0,
    "flemmix": 3.0,
    "darkiworld": 0.8,
}

# Frontière : temps de construction (sitemaps / pagination), hors fiches
FRONTIERE = {"frenchstream": 12, "franime": 3, "coflix": 90,
             "wawacity": 1800, "monstream": 5, "flemmix": 5, "darkiworld": 5}


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
        pause = s.pause if s.pause != 3.0 else c.get("pause", s.pause)
        surcout = SURCOUT.get(n, 1.0)
        if not s.joueurs:
            surcout = min(surcout, 1.5)
        secondes = fiches * (pause + surcout) + FRONTIERE.get(n, 0)
        lignes.append({"source": n, "fiches_mesurees": fiches,
                       "pause_s": pause, "surcout_s": surcout,
                       "secondes": round(secondes),
                       "heures": round(secondes / 3600, 1),
                       "jours": round(secondes / 86400, 2)})
    total_seq = sum(x["secondes"] for x in lignes)
    mur = max((x["secondes"] for x in lignes), default=0)
    goulot = max(lignes, key=lambda x: x["secondes"])["source"] if lignes else None
    return {
        "sources_actives": len(lignes),
        "total_fiches": sum(x["fiches_mesurees"] for x in lignes),
        "par_source": lignes,
        "sequentiel_1_worker": {"heures": round(total_seq / 3600, 1),
                                "jours": round(total_seq / 86400, 2)},
        "parallele_1_worker_par_source": {"heures": round(mur / 3600, 1),
                                          "jours": round(mur / 86400, 2),
                                          "goulot": goulot,
                                          "gain": round(total_seq / mur, 1) if mur else 0},
        "sessions_colab_12h_necessaires": -(-int(mur / 3600) // 12) if mur else 0,
        "gpu": "aucun effet : Chrome, le parsing HTML et le réseau sont CPU/RAM/bande passante, pas GPU",
        "hypotheses": "catalogues mesurés le 2026-11-02 ; hors pannes, hors changement de domaine",
    }
