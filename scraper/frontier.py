"""Construction de la file d'attente : sitemap, index de sitemaps, pagination.

Les <loc> de FrenchStream pointent vers un ANCIEN domaine : on garde le chemin
canonique et on réécrit l'hôte vers le miroir actif. C'est le chemin, pas le
domaine, qui sert d'identité (les domaines changent plusieurs fois par an).
"""

from __future__ import annotations

import concurrent.futures
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .config import USER_AGENT


def maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(url: str, timeout: int = 40, ua: str = USER_AGENT,
        essais: int = 3) -> tuple[int, str]:
    """GET avec retries : les IP de datacenter GitHub essuient des 403 ponctuels.

    Aucune rotation d'IP, aucun contournement : on réessaie simplement la même
    URL avec un court délai, puis on abandonne proprement.
    """
    headers = {"User-Agent": ua, "Accept-Language": "fr-FR,fr;q=0.9",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Encoding": "identity"}
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status == 200:
                    return r.status, r.read(30_000_000).decode("utf-8", "ignore")
                code = r.status
        except Exception:
            code = 0
        if i < essais - 1:
            time.sleep(1.2 * (i + 1))
    return code, ""


def miroir_actif(cfg_source: dict, timeout: int = 25) -> str | None:
    for domaine in cfg_source["mirrors"]:
        code, html = get(f"https://{domaine}{cfg_source['home']}", timeout)
        marqueur = cfg_source.get("home_marker", "").lower()
        if code == 200 and (not marqueur or marqueur in html.lower()):
            return domaine
    return None


def normaliser(url: str, domaine: str, garder_query: bool = False) -> tuple[str, str] | None:
    p = urllib.parse.urlparse(url)
    chemin = p.path.rstrip("/") or "/"
    if garder_query and p.query:
        chemin += "?" + p.query
    if not chemin.startswith("/"):
        return None
    return f"https://{domaine}{chemin}", chemin


def urls_sitemap(domaine: str, chemin_sitemap: str, timeout: int = 40,
                 index: bool = False, pause: float = 0.1, max_urls: int = 0):
    """Renvoie (url, lastmod|None). Suit un index de sitemaps si index=True."""
    # Certains miroirs renvoient un 403 ponctuel sur /sitemap.xml mais répondent
    # sur /sitemap_index.xml ou /wp-sitemap.xml : on essaie les chemins connus.
    candidats = list(dict.fromkeys(
        [chemin_sitemap] + (["/sitemap_index.xml", "/wp-sitemap.xml", "/sitemap.xml"]
                            if index else [])))
    texte = ""
    for chemin in candidats:
        code, t = get(f"https://{domaine}{chemin}", timeout)
        if code == 200 and t:
            texte = t
            if not index or "<sitemap" in t:
                break
    if not texte:
        return []
    if "<sitemap" in texte and "<sitemapindex" in texte or (index and "<sitemap>" in texte):
        enfants = re.findall(r"<loc>\s*(.*?)\s*</loc>", texte, re.S | re.I)
        # Les sitemaps de pages/catégories ne contiennent pas de fiches :
        # on les passe en dernier pour que --limit tombe tout de suite sur du contenu.
        enfants.sort(key=lambda u: 1 if re.search(
            r"/(page|category|author|tag|post)-sitemap", u, re.I) else 0)
        out = []
        # 4 requêtes concurrentes sur des fichiers XML statiques, c'est l'usage
        # normal d'un index de sitemap ; aucune fiche n'est encore visitée ici.
        def lire(u):
            c2, t2 = get(u, timeout)
            if c2 != 200:
                return []
            res = []
            for bloc in re.findall(r"<url>(.*?)</url>", t2, re.S | re.I):
                loc = re.search(r"<loc>\s*(.*?)\s*</loc>", bloc, re.S | re.I)
                if not loc:
                    continue
                lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", bloc, re.S | re.I)
                res.append((loc.group(1).strip(), lm.group(1).strip() if lm else None))
            return res
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            for res in ex.map(lire, enfants):
                out.extend(res)
                if max_urls and len(out) >= max_urls:
                    break
        return out[:max_urls] if max_urls else out
    out = []
    for bloc in re.findall(r"<url>(.*?)</url>", texte, re.S | re.I):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", bloc, re.S | re.I)
        if not loc:
            continue
        lm = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", bloc, re.S | re.I)
        out.append((loc.group(1).strip(), lm.group(1).strip() if lm else None))
    return out


def urls_pagination(cfg: dict, domaine: str, max_pages: int = 0,
                    pause: float = 0.3) -> list[tuple[str, str | None]]:
    """Wawacity : pas de sitemap utile → on parcourt les pages de listing.

    On lit d'abord la 1re page pour découvrir le numéro de la dernière, puis on
    relève les liens de fiches sur chaque page. Ce sont des pages de LISTE,
    petites et prévues pour être parcourues ; la pause reste appliquée.
    """
    liens: dict[str, str | None] = {}
    motif = re.compile(cfg["fiche"])
    for listing in cfg.get("listing", []):
        base = f"https://{domaine}{listing}"
        code, html = get(base, 20)
        if code != 200:
            continue
        pages = [int(x) for x in re.findall(r"[?&]page=(\d+)", html)]
        derniere = max(pages) if pages else 1
        if max_pages:
            derniere = min(derniere, max_pages)
        for n in range(1, derniere + 1):
            code, t = get(f"{base}&page={n}", 20) if "?" in base else get(f"{base}?page={n}", 20)
            if code != 200:
                continue
            for m in motif.finditer(t):
                url = m.group(0)
                if url.startswith("?"):
                    url = f"https://{domaine}/{url}"
                elif url.startswith("/"):
                    url = f"https://{domaine}{url}"
                liens[url] = None
            time.sleep(pause)
    return list(liens.items())


def construire(source: str, cfg_source: dict, domaine: str, robots,
               incremental: bool = True, limite: int | None = None,
               max_pages: int = 0, pause_pagination: float = 0.3) -> list[dict]:
    mode = cfg_source.get("mode", "sitemap")
    if mode == "pagination":
        brut = urls_pagination(cfg_source, domaine, max_pages, pause_pagination)
    elif mode == "sitemap_index":
        # En mode test (--limit), on ne lit qu'une partie de l'index.
        brut = urls_sitemap(domaine, cfg_source["sitemap"], index=True,
                            max_urls=(limite * 4 if limite else 0))
    elif mode == "sitemap":
        brut = urls_sitemap(domaine, cfg_source["sitemap"])
    else:
        return []
    garder_query = mode == "pagination"
    items, vus = [], set()
    for url, lastmod in brut:
        n = normaliser(url, domaine, garder_query=garder_query)
        if not n:
            continue
        cible, chemin = n
        if chemin in vus:
            continue
        vus.add(chemin)
        if cfg_source.get("include") and not any(re.search(m, chemin) for m in cfg_source["include"]):
            continue
        if any(x and x in chemin for x in cfg_source.get("exclude", [])):
            continue
        if not robots.ok(cible):
            continue
        items.append({"source": source, "canonical_path": chemin,
                      "url": cible, "lastmod": lastmod,
                      "first_seen": maintenant(), "status": "pending"})
        if limite and len(items) >= limite:
            break
    return items
