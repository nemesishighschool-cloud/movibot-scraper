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
    # FrenchStream affiche « Connexion requise » pour ses fonctions de compte
    # (ma liste, favoris) : cela ne concerne PAS la lecture. On ne le note que
    # pour les sources dont la lecture elle-même est verrouillée.
    if item["source"] == "franime" and re.search(
            r"connexion requise|connectez-vous|login required", texte, re.I):
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


# ─── Extracteur générique (Coflix, Wawacity, sources futures) ────────────────

def _premier(s, selecteurs):
    for sel in selecteurs:
        e = s.select_one(sel)
        if e:
            t = e.get_text(" ", strip=True)
            if t and len(t) < 300:
                return t
    return ""


def extraire_generique(html: str, item: dict, cfg: dict | None = None) -> dict:
    """Extraction souple pour les sites non-DLE, pilotée par `cfg['selecteurs']`."""
    cfg = cfg or {}
    s = BeautifulSoup(html, "html.parser")
    for tag in s(["script", "style", "noscript", "svg"]):
        tag.decompose()
    texte = s.get_text(" ", strip=True)
    og = lambda k: (s.find("meta", property="og:" + k) or {}).get("content", "") or ""
    sel = cfg.get("selecteurs", {})

    titre = _premier(s, sel.get("titre", ["h1"])) or og("title") or ""
    titre = re.sub(r"^(?:télécharger|regarder|voir|films?|séries?)\s+", "", titre, flags=re.I)
    titre = re.sub(r"\s*(?:gratuitement\s+)?sur\s+wawacity.*$", "", titre, flags=re.I)
    titre = re.sub(r"\s*[|✅].*$", "", titre).strip()
    # Wawacity : « Films » Fight Club [BLURAY 4K] - MULTI (TRUEFRENCH) »
    if item["source"] == "wawacity":
        titre = re.sub(r"^.*?»\s*", "", titre)
        titre = re.sub(r"\s*\[[^\]]*\]", "", titre)          # qualité
        titre = re.sub(r"\s*-\s*(MULTI|VO|VF|TRUEFRENCH).*$", "", titre, flags=re.I)
    titre = titre.strip()[:180]
    if titre.lower() in ("connexion requise", "signaler un problème", ""):
        titre = og("title") or titre

    chemin = item["canonical_path"]
    if re.search(r"/serie/|p=serie", chemin):
        kind = "serie"
    elif re.search(r"/anime/|p=manga", chemin):
        kind = "anime"
    elif re.search(r"/film/|p=film", chemin):
        kind = "film"
    else:
        kind = "serie" if re.search(r"saison|épisode", titre, re.I) else "film"

    # « Année: 1999 » du bloc de détails est la source la plus fiable ; sinon
    # l'année du chemin/titre. On évite de prendre l'année courante du pied de page.
    m = re.search(r"Ann[ée]e\s*:\s*((?:19|20)\d{2})", texte[:4000], re.I)
    if not m:
        m = re.search(r"\b((?:19|20)\d{2})\b", chemin + " " + titre)
    if not m and item["source"] != "wawacity":
        m = re.search(r"\b((?:19|20)\d{2})\b", texte[:1200] + " " + og("description"))
    annee = int(m.group(1)) if m else None
    m = re.search(r"saison\s*(\d{1,2})", titre, re.I)
    saison = int(m.group(1)) if m else None
    duree = None
    # « Durée: 02h19 » se trouve souvent dans og:description, pas dans le texte visible.
    source_duree = texte[:1200] + " " + og("description")
    m = re.search(r"Durée\s*:\s*(\d{1,2})h(\d{2})", source_duree, re.I)
    if m:
        duree = int(m.group(1)) * 60 + int(m.group(2))
    else:
        m = re.search(r"\b(\d{2,3})\s*min\b", source_duree, re.I)
        duree = int(m.group(1)) if m else None

    syn = _premier(s, sel.get("synopsis", []))
    if len(syn) < 30:
        syn = og("description") or ""
    if len(syn) < 30:
        m = s.find("meta", attrs={"name": "description"})
        syn = (m.get("content") or "") if m else syn

    affiche = og("image") or ""
    if not affiche:
        img = s.select_one("img[src*='tmdb'], img[src*='poster'], img[src*='/img/films/']")
        affiche = (img.get("src") or img.get("data-src") or "") if img else ""

    ep = None
    if sel.get("episodes"):
        ep = len(s.select(",".join(sel["episodes"]))) or None
    if ep is None:
        m = re.search(r"(\d{1,3})\s*[ée]pisodes?", texte[:1500], re.I)
        ep = int(m.group(1)) if m else None

    genres = []
    mg = re.search(r"Genre\(s\)\s*:\s*([^|]{3,120})", texte[:4000], re.I)
    if mg:
        bloc = re.split(r"Bande annonce|Partager|Titre original|Nationalit[ée]|R[ée]alisateur|Acteurs|Dur[ée]e",
                        mg.group(1), flags=re.I)[0]
        genres = [x.strip() for x in re.split(r"[,/]", bloc)
                  if x.strip() and len(x.strip()) < 30][:6]
    if not genres:
        genres = [g for g in GENRES if re.search(r"\b" + re.escape(g) + r"\b", texte[:2500], re.I)]
    langues = sorted(set(re.findall(r"\b(?:VF|VOSTFR|VOST|VO|MULTI|TRUEFRENCH)\b",
                                    texte[:2500], re.I)))

    notes = []
    if re.search(r"connexion requise|connectez-vous", texte, re.I):
        notes.append("lecture soumise à connexion sur le site source")
    if not affiche:
        notes.append("affiche absente")
    if item["source"] == "wawacity":
        notes.append("site de téléchargement direct, pas de lecteur intégré")

    return {
        "source": item["source"], "source_domain": item.get("source_domain", ""),
        "canonical_path": chemin, "page_url": item["url"],
        "title": titre, "kind": kind, "year": annee, "season": saison,
        "episode_count": ep,
        "languages": __import__("json").dumps(langues, ensure_ascii=False),
        "genres": __import__("json").dumps(genres[:6], ensure_ascii=False),
        "duration_min": duree, "synopsis": syn[:600], "poster_url": affiche,
        "players": "[]", "embed_url": None, "download_url": None,
        "lastmod": item.get("lastmod"), "first_seen": item.get("first_seen"),
        "status": "ok", "error": None,
        "notes": " ; ".join(notes) if notes else None,
    }
