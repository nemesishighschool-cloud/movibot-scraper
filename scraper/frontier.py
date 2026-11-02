"""Construction de la file d'attente à partir des sitemaps.

Les <loc> de FrenchStream pointent vers un ANCIEN domaine : on garde le chemin
canonique et on réécrit l'hôte vers le miroir actif. C'est le chemin, pas le
domaine, qui sert d'identité (les domaines changent plusieurs fois par an).
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .config import USER_AGENT


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url: str, timeout: int = 40, ua: str = USER_AGENT) -> tuple[int, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua,
                                                   "Accept-Language": "fr-FR,fr;q=0.9"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(30_000_000).decode("utf-8", "ignore")
    except Exception:
        return 0, ""


def miroir_actif(cfg_source: dict, timeout: int = 12) -> str | None:
    """Teste les miroirs dans l'ordre et renvoie le premier sain."""
    for domaine in cfg_source["mirrors"]:
        code, html = get(f"https://{domaine}{cfg_source['home']}", timeout)
        marqueur = cfg_source.get("home_marker", "").lower()
        if code == 200 and (not marqueur or marqueur in html.lower()):
            return domaine
    return None


def normaliser(url: str, domaine: str) -> tuple[str, str] | None:
    p = urllib.parse.urlparse(url)
    chemin = p.path.rstrip("/") or "/"
    if not chemin.startswith("/"):
        return None
    return f"https://{domaine}{chemin}", chemin


def urls_sitemap(domaine: str, chemin_sitemap: str, timeout: int = 40):
    """Renvoie (url, lastmod|None) pour chaque entrée <url> du sitemap."""
    code, texte = get(f"https://{domaine}{chemin_sitemap}", timeout)
    if code != 200 or "<urlset" not in texte and "<url>" not in texte:
        return []
    out = []
    for bloc in re.findall(r"<url>(.*?)</url>", texte, re.S | re.I):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", bloc, re.S | re.I)
        if not loc:
            continue
        lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", bloc, re.S | re.I)
        out.append((loc.group(1).strip(), lm.group(1).strip() if lm else None))
    return out


def construire(source: str, cfg_source: dict, domaine: str, robots,
               incremental: bool = True, limite: int | None = None) -> list[dict]:
    """Filtre les URLs du sitemap par robots.txt et par motifs de la source."""
    items = []
    vus = set()
    for url, lastmod in urls_sitemap(domaine, cfg_source["sitemap"]):
        n = normaliser(url, domaine)
        if not n:
            continue
        cible, chemin = n
        if chemin in vus:
            continue
        vus.add(chemin)
        if not any(re.search(m, chemin) for m in cfg_source["include"]):
            continue
        if any(x and x in chemin for x in cfg_source["exclude"]):
            continue
        if not robots.ok(cible):
            continue
        items.append({"source": source, "canonical_path": chemin,
                      "url": cible, "lastmod": lastmod,
                      "first_seen": maintenant(), "status": "pending"})
        if limite and len(items) >= limite:
            break
    return items
