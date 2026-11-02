"""Boucle d'indexation : séquentielle, lente, reprenable, sans vidéo."""

from __future__ import annotations

import signal
import sys
import time

from .config import SOURCES, Settings
from .extract import extraire
from .frontier import construire, get, miroir_actif, maintenant
from .players import resoudre
from .robots import Robots, telecharger
from .storage import ajouter_frontiere, echec, enregistrer, ouvrir, stats, suivants


class ArretPropre(Exception):
    pass


def _arreter(sig, frame):
    raise ArretPropre()


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def preparer(c, s: Settings):
    """Teste les miroirs, lit les robots et remplit la frontière."""
    actifs, textes = {}, {}
    for source, cfg in SOURCES.items():
        if s.source and source != s.source:
            continue
        domaine = miroir_actif(cfg)
        if not domaine:
            log(f"⚠️ {source} : aucun miroir sain, source différée")
            continue
        actifs[source] = domaine
        textes[domaine] = telecharger(domaine, s.ua)
        log(f"✅ {source} → miroir actif {domaine}")
    robots = Robots(textes)
    for source, domaine in actifs.items():
        items = construire(source, SOURCES[source], domaine, robots,
                           incremental=s.incremental, limite=s.limite)
        n = ajouter_frontiere(c, items, s.incremental)
        log(f"   frontière {source} : {len(items)} URLs, {n} nouvelles/à revoir")
    return actifs, robots


def viser_fiche(page, url: str, s: Settings) -> str:
    """Charge une fiche et laisse finir la vérification JavaScript si besoin."""
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


def executer(s: Settings) -> dict:
    signal.signal(signal.SIGINT, _arreter)
    signal.signal(signal.SIGTERM, _arreter)
    c = ouvrir(s.db)
    debut = maintenant()
    actifs, _ = preparer(c, s)
    if not actifs:
        log("Aucune source joignable : arrêt propre, rien n'est perdu.")
        return {"ok": False, "raison": "aucun miroir"}

    a_traiter = suivants(c, s.source, s.limite)
    log(f"▶ {len(a_traiter)} fiches à visiter | pause {s.pause}s | "
        f"joueurs={'oui' if s.joueurs else 'non'}")
    if not a_traiter:
        return {"ok": True, "nouvelles": 0}

    t0, ok, erreurs, consecutives = time.time(), 0, 0, 0
    besoin_navigateur = any(SOURCES[x]["needs_browser"] for x in actifs)
    navigateur, b, ctx, page = None, None, None, None

    try:
        if besoin_navigateur:
            from playwright.sync_api import sync_playwright
            navigateur = sync_playwright().start()
            b = navigateur.chromium.launch(headless=True, args=["--no-sandbox"])
            ctx = b.new_context(user_agent=s.ua, locale="fr-FR",
                                viewport={"width": 1366, "height": 900})
            ctx.route("**/*", lambda route: route.abort()
                      if route.request.resource_type in ("image", "media", "font")
                      else route.continue_())
            page = ctx.new_page()
            premier = next(x for x in actifs if SOURCES[x]["needs_browser"])
            try:
                page.goto(f"https://{actifs[premier]}{SOURCES[premier]['home']}",
                          wait_until="domcontentloaded", timeout=s.timeout * 1000)
                page.wait_for_timeout(1800)
            except Exception as e:
                log(f"accueil : {type(e).__name__} (on continue)")
        else:
            b = ctx = page = None

        for n, item in enumerate(a_traiter, 1):
            source = item["source"]
            cfg = SOURCES[source]
            domaine = actifs.get(source)
            if not domaine:
                continue
            d = None
            try:
                if cfg["needs_browser"]:
                    html = viser_fiche(page, item["url"], s)
                else:
                    code, html = get(item["url"], timeout=s.timeout, ua=s.ua)
                    if code != 200:
                        raise RuntimeError(f"HTTP {code}")
                d = extraire(html, {**item, "source_domain": domaine})
                if not d["title"] or len(html) < 4000:
                    d["status"] = "partiel"
                if s.joueurs and cfg["needs_browser"] and cfg["player_buttons"]:
                    joueurs = resoudre(page, cfg, sonder=s.sonder)
                    if joueurs:
                        import json as _json
                        d["players"] = _json.dumps(joueurs, ensure_ascii=False)
                        d["embed_url"] = joueurs[0]["embed_url"]
                        d["download_url"] = joueurs[0]["download_url"]
                        d["etat_lecteur"] = joueurs[0].get("etat", "pret")
                    else:
                        d["notes"] = " ; ".join(filter(None, [d.get("notes"),
                                                   "identifiant de lecteur non exposé"]))
                enregistrer(c, d)
                ok += 1
                consecutives = 0
            except Exception as e:
                erreurs += 1
                consecutives += 1
                echec(c, item["canonical_path"], f"{type(e).__name__}: {str(e)[:120]}")
                log(f"  ✗ {item['canonical_path'][:55]} : {type(e).__name__}")
                if consecutives >= s.max_erreurs:
                    log(f"⛔ {consecutives} erreurs consécutives : arrêt propre, "
                        "relance plus tard (rien n'est perdu)")
                    break
            c.execute("INSERT OR REPLACE INTO progress VALUES (?,?,?,?)",
                      (source, n, len(a_traiter), maintenant()))
            c.commit()
            if n % 10 == 0 or n == len(a_traiter):
                log(f"[{n}/{len(a_traiter)}] {ok} ok / {erreurs} erreurs | "
                    f"{time.time()-t0:.0f}s | {str(d.get('title') if d else '')[:40]}")
            time.sleep(s.pause)

        if b:
            b.close()
    except ArretPropre:
        log("⏹ Interruption demandée : état sauvegardé, relance = reprise.")
    finally:
        if navigateur:
            navigateur.stop()
        c.execute("INSERT INTO runs (started_at, ended_at, inserted, errors, note) "
                  "VALUES (?,?,?,?,?)",
                  (debut, maintenant(), ok, erreurs, "daemon"))
        c.commit()
        bilan = stats(c)
        log(f"TERMINÉ | {bilan['fiches']} fiches | {ok} nouvelles | "
            f"{bilan['en_attente']} restantes | {time.time()-t0:.0f}s")
        resultat = {"ok": True, "nouvelles": ok, "erreurs": erreurs,
                    "duree": round(time.time() - t0, 1), **bilan}
        c.close()
    return resultat
