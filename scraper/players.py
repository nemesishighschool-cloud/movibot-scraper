"""Résolution des lecteurs.

Les fiches n'exposent souvent PAS l'identifiant du lecteur dans leur HTML :
il apparaît quand on clique sur l'onglet Vidzy / Voe / Netu (action normale
d'un utilisateur, aucun contournement). On clique donc ces onglets dans la
même page de navigateur, puis on relève les iframes.

Aucun flux vidéo n'est téléchargé : on ne lit que le petit HTML du lecteur.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from .config import EMBED_HOSTS, USER_AGENT
from .extract import identifiants_dans_html


def sonde(url: str, timeout: int = 10) -> dict:
    """Diagnostic : le lecteur est-il prêt, en attente (~180 s), ou limité ?"""
    r = {"url": url, "etat": "erreur", "http": None, "flux": 0,
         "octets": None, "x_frame_options": None}
    h = urllib.parse.urlparse(url).hostname or ""
    if not any(h == d or h.endswith("." + d) for d in EMBED_HOSTS):
        r["etat"] = "refuse"
        return r
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Referer": "https://fs26.lol/"})
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            corps = rep.read(250000)
            t = corps.decode("utf-8", "ignore")
            r.update(http=rep.status, octets=len(corps),
                     x_frame_options=rep.headers.get("X-Frame-Options") or "absent",
                     flux=len(re.findall(r"\.m3u8|\.mp4", t, re.I)))
        if "Chargement vidéo" in t or "totalDuration" in t:
            r["etat"] = "attente"
        elif r["flux"] > 0 and str(r["x_frame_options"]).lower() in ("absent", "none", ""):
            r["etat"] = "pret"
        else:
            r["etat"] = "limite"
    except Exception:
        r["etat"] = "erreur"
    return r


def url_download(url_embed: str) -> str | None:
    m = re.match(r"https?://([^/]+)/embed-([A-Za-z0-9]+)\.html", url_embed)
    if not m:
        return None
    return f"https://{m.group(1)}/d/{m.group(2)}.html"


def host_depuis(url: str) -> str:
    h = urllib.parse.urlparse(url).hostname or ""
    if "vidzy" in h:
        return "Vidzy"
    if "fsvid" in h:
        return "Vidzy"
    if "voe" in h:
        return "Voe"
    if "netu" in h:
        return "Netu"
    if "vidl" in h or "uqload" in h:
        return "Uqload"
    return h


def resoudre(page, cfg_source: dict, sonder: bool = False) -> list[dict]:
    """Clique les onglets de lecteurs et renvoie les URLs trouvées."""
    trouves: dict[str, dict] = {}

    def collecter():
        try:
            html = page.content()
        except Exception:
            return
        for ident in identifiants_dans_html(html):
            u = f"https://vidzy.org/embed-{ident}.html"
            trouves.setdefault(u, {"host": "Vidzy", "embed_url": u,
                                   "download_url": url_download(u)})
        for f in page.locator("iframe").all():
            src = f.get_attribute("src") or ""
            if "/embed-" not in src:
                continue
            src = src.split("?")[0]
            if not src.startswith("http"):
                continue
            trouves.setdefault(src, {"host": host_depuis(src), "embed_url": src,
                                     "download_url": url_download(src)})

    collecter()                                    # déjà visibles dans la fiche
    for libelle in cfg_source.get("player_buttons", []):
        try:
            bouton = page.get_by_text(libelle, exact=False).first
            if bouton.count() == 0:
                continue
            bouton.click(timeout=4000)
            page.wait_for_timeout(1200)
            collecter()
        except Exception:
            continue                                # onglet absent ou non cliquable
    if sonder:
        for p in trouves.values():
            p["etat"] = sonde(p["embed_url"])["etat"]
    return list(trouves.values())
