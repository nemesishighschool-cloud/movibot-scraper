"""Configuration du moteur de scraping. Aucun secret dans ce fichier."""

from __future__ import annotations

import os

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"}

# Miroirs classés par priorité. FrenchStream change plusieurs fois par an :
# le moteur teste chaque miroir au démarrage et bascule automatiquement.
SOURCES = {
    "frenchstream": {
        "mirrors": ["fs26.lol", "french-stream.net", "fs27.lol"],
        "sitemap": "/sitemap.xml",
        "home": "/",
        "home_marker": "French Stream",
        "needs_browser": True,          # page « Verification... » sur les fiches
        "include": [r"\.html$"],
        "exclude": ["xfsearch", "/user/", "/newposts/", "/statistics.html",
                    "/inscription", "/premium.php", "/hists/", "/engine/",
                    "/tags/", "/news/", "subaction=userinfo", "do=search",
                    "do=xfsearch", "print=", "/page/"],
        "player_buttons": ["Vidzy", "Voe", "Netu"],
    },
    "franime": {
        # franime.me / franime.tv interdisent nommément les crawlers d'IA dans
        # leur robots.txt → volontairement écartés. franime.org : search=yes.
        "mirrors": ["franime.org"],
        "sitemap": "/sitemap.xml",
        "home": "/",
        "home_marker": "FRAnime",
        "needs_browser": False,
        "include": [r"/catalogue/[^/?#]+$"],
        "exclude": ["/api/", "/catalogue?q=", "/surprise", "/auth", "/aide",
                    "/contact", "/catalogue$"],
        "player_buttons": [],           # lecture soumise à connexion
    },
}

GENRES = ["Action", "Aventure", "Animation", "Arts Martiaux", "Biopic", "Comédie",
          "Drame", "Documentaire", "Horreur", "Historique", "Espionnage", "Famille",
          "Fantastique", "Guerre", "Policier", "Romance", "Science fiction",
          "Spectacle", "Thriller", "Western", "Mystère", "Crime", "Kids",
          "Action & Adventure", "Science-Fiction & Fantastique"]
HOSTS = ("Vidzy", "Voe", "Netu", "Uqload")
EMBED_HOSTS = ("vidzy.org", "fsvid.lol", "voe.sx", "netu.tv", "vidl.lol")


def charge_env(path: str = "config.env") -> None:
    """Charge un fichier .env simple sans dépendance externe."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def opt(cle: str, defaut):
    return os.environ.get(cle, defaut)


class Settings:
    def __init__(self):
        charge_env(opt("SCRAPER_ENV", "config.env"))
        self.db = opt("SCRAPER_DB", "data/index_web.sqlite3")
        self.pause = float(opt("SCRAPER_PAUSE", "3.0"))       # secondes entre 2 fiches
        self.timeout = int(opt("SCRAPER_TIMEOUT", "35"))      # secondes par page
        self.max_erreurs = int(opt("SCRAPER_MAX_ERREURS", "8"))
        self.limite = int(opt("SCRAPER_LIMIT", "0")) or None
        self.source = opt("SCRAPER_SOURCE", "") or None
        self.joueurs = opt("SCRAPER_PLAYERS", "1") != "0"
        self.sonder = opt("SCRAPER_PROBE", "0") == "1"
        self.incremental = opt("SCRAPER_INCREMENTAL", "1") != "0"
        self.ua = opt("SCRAPER_UA", USER_AGENT)
        self.log = opt("SCRAPER_LOG", "data/scraper.log")
