"""Boucle d'indexation : une instance de navigateur PAR SOURCE, jamais deux
sur le même domaine. Parallélisme inter-sources uniquement, pauses respectées.

Chaque worker possède sa propre connexion SQLite (WAL) et son propre Chromium.
Chaque fiche est écrite avant de passer à la suivante → reprise sans doublon.
"""

from __future__ import annotations

import concurrent.futures
import signal
import threading
import time

from .config import SOURCES, Settings, actives
from .extract import extraire, extraire_generique
from .frontier import construire, get, miroir_actif, maintenant
from .players import resoudre
from .robots import Robots, telecharger
from .storage import ajouter_frontiere, echec, enregistrer, ouvrir, stats, suivants

ARRET = threading.Event()


def _arreter(sig, frame):
    ARRET.set()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def preparer(c, s: Settings):
    """Teste les miroirs, lit les robots et remplit la frontière (une fois)."""
    actifs, textes = {}, {}
    for source in actives():
        if s.source and source != s.source:
            continue
        cfg = SOURCES[source]
        domaine = miroir_actif(cfg)
        if not domaine:
            log(f"⚠️ {source} : aucun miroir sain, source différée")
            continue
        actifs[source] = domaine
        textes[domaine] = telecharger(domaine, s.ua)
        log(f"✅ {source:13} → {domaine}")
    robots = Robots(textes)
    for source, domaine in actifs.items():
        avant = time.time()
        items = construire(source, SOURCES[source], domaine, robots,
                           incremental=s.incremental, limite=s.limite,
                           max_pages=s.max_pages,
                           pause_pagination=s.pause_pagination)
        n = ajouter_frontiere(c, items, s.incremental)
        log(f"   frontière {source:13} : {len(items):6} URLs, {n:6} nouvelles "
            f"({time.time()-avant:.0f}s)")
    return actifs, robots


def viser_fiche(page, url: str, s: Settings) -> str:
    html = ""
    for essai in range(3):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=s.timeout * 1000)
            page.wait_for_timeout(900)
            html = page.content()
            if "Verification" in html[:2000] and len(html) < 12000:
                page.wait_for_timeout(2500)
                html = page.content()
            break
        except Exception:
            if essai == 2:
                raise
            page.wait_for_timeout(1500)
    return html


def _checkpoint(c, s, compteur):
    if s.checkpoint and compteur and compteur % s.checkpoint_every == 0:
        try:
            import os
            import sqlite3
            os.makedirs(os.path.dirname(s.checkpoint) or ".", exist_ok=True)
            dst = sqlite3.connect(s.checkpoint)
            c.backup(dst)
            dst.close()
            log(f"   ☁️ checkpoint → {s.checkpoint} ({compteur} fiches)")
        except Exception as e:
            log(f"   ⚠️ checkpoint échoué : {type(e).__name__}")


def executer_source(s: Settings, actifs: dict, robots, source: str) -> dict:
    """Un worker = une source = un domaine = un navigateur."""
    c = ouvrir(s.db)
    domaine = actifs[source]
    cfg = SOURCES[source]
    a_traiter = suivants(c, source, s.limite)
    log(f"▶ {source:13} : {len(a_traiter)} fiches | pause {s.pause}s")
    if not a_traiter:
        c.close()
        return {"source": source, "nouvelles": 0, "erreurs": 0}

    t0, ok, erreurs, consecutives = time.time(), 0, 0, 0
    navigateur = b = page = None
    try:
        if cfg["needs_browser"]:
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as e:
                raise RuntimeError(
                    "Playwright absent : pip install playwright && "
                    "python -m playwright install chromium && "
                    "python -m playwright install-deps chromium") from e
            navigateur = sync_playwright().start()
            b = navigateur.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = b.new_context(user_agent=s.ua, locale="fr-FR",
                                viewport={"width": 1366, "height": 900})
            ctx.route("**/*", lambda route: route.abort()
                      if route.request.resource_type in ("image", "media", "font")
                      else route.continue_())
            page = ctx.new_page()
            try:
                page.goto(f"https://{domaine}{cfg['home']}",
                          wait_until="domcontentloaded", timeout=s.timeout * 1000)
                page.wait_for_timeout(1800)
            except Exception as e:
                log(f"   accueil {source} : {type(e).__name__} (on continue)")

        # Pause par source, jamais en dessous du robots.txt. Un --pause explicite
        # (différent du défaut 3.0) reste prioritaire.
        base = s.pause if s.pause != 3.0 else cfg.get("pause", s.pause)
        pause_domaine = max(base, robots.pause(domaine) or 0,
                            cfg.get("crawl_delay", 0) or 0)
        for n, item in enumerate(a_traiter, 1):
            if ARRET.is_set():
                log(f"⏹ {source} : arrêt demandé, état sauvegardé")
                break
            d = None
            try:
                if cfg["needs_browser"]:
                    html = viser_fiche(page, item["url"], s)
                else:
                    code, html = get(item["url"], timeout=s.timeout, ua=s.ua)
                    if code != 200:
                        raise RuntimeError(f"HTTP {code}")
                if cfg.get("extracteur") == "generique":
                    d = extraire_generique(html, {**item, "source_domain": domaine}, cfg)
                else:
                    d = extraire(html, {**item, "source_domain": domaine})
                if not d["title"] or len(html) < 4000:
                    d["status"] = "partiel"
                if s.joueurs and cfg["needs_browser"] and cfg.get("player_buttons"):
                    joueurs = resoudre(page, cfg, sonder=s.sonder)
                    if joueurs:
                        import json
                        d["players"] = json.dumps(joueurs, ensure_ascii=False)
                        d["embed_url"] = joueurs[0]["embed_url"]
                        d["download_url"] = joueurs[0]["download_url"]
                        d["etat_lecteur"] = joueurs[0].get("etat", "pret")
                enregistrer(c, d)
                ok += 1
                consecutives = 0
                _checkpoint(c, s, ok)
            except Exception as e:
                erreurs += 1
                consecutives += 1
                echec(c, item["canonical_path"], f"{type(e).__name__}: {str(e)[:120]}")
                if consecutives >= s.max_erreurs:
                    log(f"⛔ {source} : {consecutives} erreurs consécutives, arrêt propre")
                    break
            c.execute("INSERT OR REPLACE INTO progress VALUES (?,?,?,?)",
                      (source, n, len(a_traiter), maintenant()))
            c.commit()
            if n % 25 == 0 or n == len(a_traiter):
                log(f"   [{source}:{n}/{len(a_traiter)}] {ok} ok / {erreurs} err | "
                    f"{time.time()-t0:.0f}s")
            time.sleep(pause_domaine)
        if b:
            b.close()
    except Exception as e:
        log(f"⛔ {source} : {type(e).__name__}: {str(e)[:120]}")
        erreurs += 1
    finally:
        if navigateur:
            navigateur.stop()
        _checkpoint(c, s, ok)
        c.execute("INSERT INTO runs (started_at, ended_at, inserted, errors, note) "
                  "VALUES (?,?,?,?,?)", (maintenant(), maintenant(), ok, erreurs, source))
        c.commit()
        c.close()
    return {"source": source, "nouvelles": ok, "erreurs": erreurs,
            "duree": round(time.time() - t0, 1)}


def executer(s: Settings) -> dict:
    signal.signal(signal.SIGINT, _arreter)
    signal.signal(signal.SIGTERM, _arreter)
    ARRET.clear()
    c = ouvrir(s.db)
    actifs, robots = preparer(c, s)
    c.close()
    if not actifs:
        log("Aucune source joignable : arrêt propre, rien n'est perdu.")
        return {"ok": False, "raison": "aucun miroir"}
    sources = [x for x in actifs if not s.source or x == s.source]
    t0 = time.time()
    # SCRAPER_WORKERS=0 (défaut) = auto : 1 worker par source active.
    workers = s.workers if s.workers > 0 else len(sources)
    if workers > 1 and len(sources) > 1:
        n = min(workers, len(sources))
        log(f"⚡ {n} workers en parallèle (1 par source/domaine)")
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
            futures = {ex.submit(executer_source, s.clone(src), actifs, robots, src): src
                       for src in sources}
            resultats = []
            for f in concurrent.futures.as_completed(futures):
                try:
                    resultats.append(f.result())
                except Exception as e:
                    resultats.append({"source": futures[f], "erreur": str(e)[:120]})
    else:
        resultats = [executer_source(s.clone(src), actifs, robots, src)
                     for src in sources]
    c = ouvrir(s.db)
    bilan = stats(c)
    c.close()
    log(f"TERMINÉ | {bilan['fiches']} fiches | {bilan['en_attente']} restantes | "
        f"{time.time()-t0:.0f}s")
    return {"ok": True, "duree": round(time.time() - t0, 1),
            "workers": min(workers, len(sources)) if workers > 1 else 1,
            "detail_workers": resultats, **bilan}
