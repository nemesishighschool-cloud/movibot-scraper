"""Extraction des métadonnées depuis le HTML rendu.

Aucun octet de vidéo n'est téléchargé : on ne lit que du texte et des URLs.
Le texte des <script> est retiré avant analyse (il contient des chaînes d'UI
comme « Connexion requise » qui ne sont pas affichées).
"""

from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from .config import GENRES, HOSTS


def extraire(html: str, item: dict) -> dict:
    s = BeautifulSoup(html, "html.parser")
    for tag in s(["script", "style", "noscript", "svg"]):
        tag.decompose()
    texte = s.get_text(" ", strip=True)

    og = lambda k: (s.find("meta", property="og:" + k) or {}).get("content", "") or ""
    h1 = s.find("h1")
    titre = (h1.get_text(" ", strip=True) if h1 else "") or og("title") or ""
    titre = re.sub(r"^(?:film|série|serie)\s+", "", titre, flags=re.I)[:180]
    page_title = (s.title.get_text(" ", strip=True) if s.title else "").lower()

    facts = s.select_one("div.facts")
    facts_txt = facts.get_text(" ", strip=True) if facts else ""

    # Bloc DLE : -TV-14 - 2022 - Drame - 55 min
    m = re.search(r"\b((?:19|20)\d{2})\b", facts_txt + " " + titre + " " + item["canonical_path"])
    annee = int(m.group(1)) if m else None
    m = re.search(r"\b(\d{2,3})\s*min\b", facts_txt, re.I)
    duree = int(m.group(1)) if m else None
    m = re.search(r"saison\s*(\d{1,2})", titre, re.I)
    saison = int(m.group(1)) if m else None
    genres = []
    if facts:
        g = facts.select_one("span.genres")
        if g:
            genres = [x.strip() for x in re.split(r"[,/]", g.get_text(" ", strip=True)) if x.strip()]
    if not genres:
        genres = [g for g in GENRES if re.search(r"\b" + re.escape(g) + r"\b", facts_txt[:300], re.I)]

    types = {a.get("data-type", "").lower() for a in s.select(".episode-row[data-type]")}
    langues = sorted({"VF" if "vf" in t and "vost" not in t else "VOSTFR"
                      for t in types if t}) or sorted(set(
                          re.findall(r"\b(?:VF|VOSTFR|VOST|VO)\b", texte[:2500])))

    if page_title.startswith(("série", "serie")) or " saison " in page_title:
        kind = "serie"
    elif page_title.startswith("film"):
        kind = "film"
    else:
        kind = "serie" if (saison or re.search(r"saison|episode", titre, re.I)) else "film"

    syn = ""
    for sel in [".fdesc", "[itemprop=description]", ".description"]:
        e = s.select_one(sel)
        if e and len(e.get_text(" ", strip=True)) > 40:
            syn = e.get_text(" ", strip=True)
            break
    if not syn:
        syn = og("description")

    img = s.select_one("img[src*='image.tmdb.org'], .fposter img[src]")
    affiche = (img.get("src") or img.get("data-src") or "") if img else og("image")

    ep = len(s.select(".episode-row")) or None
    if ep is None:
        m = re.search(r"(\d{1,3})\s*[ée]pisodes?", texte[:1200], re.I)
        ep = int(m.group(1)) if m else None

    if item["source"] == "franime":
        kind = "anime" if "film" not in titre.lower() else "film"
        if titre and titre.islower():
            titre = titre.title()
        if annee is None:
            m = re.search(r"\b((?:19|20)\d{2})\b", texte[:400])
            annee = int(m.group(1)) if m else None
        if not langues and re.search(r"VF.{0,12}VOSTFR|VOSTFR.{0,12}VF", og("description"), re.I):
            langues = ["VF", "VOSTFR"]

    notes = []
    if re.search(r"connexion requise|connectez-vous|login required", texte, re.I):
        notes.append("lecture soumise à connexion sur le site source")
    if not affiche:
        notes.append("affiche absente")

    return {
        "source": item["source"], "source_domain": item.get("source_domain", ""),
        "canonical_path": item["canonical_path"], "page_url": item["url"],
        "title": titre, "kind": kind, "year": annee, "season": saison,
        "episode_count": ep,
        "languages": json.dumps(langues, ensure_ascii=False),
        "genres": json.dumps(genres[:6], ensure_ascii=False),
        "duration_min": duree, "synopsis": syn[:600], "poster_url": affiche,
        "players": "[]", "embed_url": None, "download_url": None,
        "lastmod": item.get("lastmod"), "first_seen": item.get("first_seen"),
        "status": "ok", "error": None,
        "notes": " ; ".join(notes) if notes else None,
    }


def identifiants_dans_html(html: str) -> list[str]:
    """IDs de lecteurs déjà visibles dans le HTML (avant tout clic)."""
    ids = re.findall(r"(?:vidzy\.org|fsvid\.lol|v6\.vidzy\w*)/embed-([A-Za-z0-9]+)\.html",
                     html, re.I)
    return list(dict.fromkeys(ids or re.findall(r"embed-([A-Za-z0-9]{8,})\.html", html, re.I)))
