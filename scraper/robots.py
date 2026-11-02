"""Lecture et respect des robots.txt (aucune tentative de contournement)."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request

from .config import USER_AGENT


def telecharger(domaine: str, ua: str = USER_AGENT, timeout: int = 12) -> str:
    try:
        req = urllib.request.Request(f"https://{domaine}/robots.txt",
                                     headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(200000).decode("utf-8", "ignore")
    except Exception:
        return ""


def analyser(texte: str, ua: str = USER_AGENT) -> dict:
    """Règles applicables à notre UA. Les blocs d'UA spécifiques sont ignorés."""
    regles, delay = [], None
    applicable = True
    for ligne in texte.splitlines():
        ligne = ligne.split("#", 1)[0].strip()
        if not ligne:
            continue
        m = re.match(r"(?i)user-agent\s*:\s*(.+)", ligne)
        if m:
            val = m.group(1).strip()
            applicable = (val == "*" or val.lower() == "generic")
            continue
        if not applicable:
            continue
        m = re.match(r"(?i)(disallow|allow)\s*:\s*(.*)", ligne)
        if m:
            chemin = m.group(2).strip()
            if chemin:
                regles.append((m.group(1).lower() == "allow", chemin))
            continue
        m = re.match(r"(?i)crawl-delay\s*:\s*([\d.]+)", ligne)
        if m:
            try:
                delay = float(m.group(1))
            except ValueError:
                pass
    return {"regles": regles, "crawl_delay": delay, "signaux": re.findall(
        r"(?im)^content-signal\s*:\s*(.+)$", texte)}


def autorisee(url: str, regles: dict) -> bool:
    """Règle standard : le préfixe le plus long gagne ; allow bat disallow à égalité."""
    chemin = urllib.parse.urlparse(url).path or "/"
    meilleur, autorisation = -1, True
    for allow, motif in regles.get("regles", []):
        if chemin.startswith(motif) or (motif.endswith("$") and chemin.endswith(motif[:-1])):
            if len(motif) >= meilleur:
                meilleur, autorisation = len(motif), allow
    return autorisation


class Robots:
    def __init__(self, domaines: dict[str, str]):
        self.par_domaine = {d: analyser(t) for d, t in domaines.items()}

    def ok(self, url: str) -> bool:
        h = urllib.parse.urlparse(url).hostname or ""
        for domaine, regles in self.par_domaine.items():
            if h == domaine or h.endswith("." + domaine):
                return autorisee(url, regles)
        return True

    def pause(self, domaine: str) -> float | None:
        return self.par_domaine.get(domaine, {}).get("crawl_delay")
