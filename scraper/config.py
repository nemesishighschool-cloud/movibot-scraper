"""Registre des sources. Aucun secret dans ce fichier.

`enabled=False` ≠ oubli : la source est gardée avec ses miroirs et la RAISON,
pour être réactivée dès qu'un domaine revient. Les domaines de ces sites
changent plusieurs fois par an ; on ne tente jamais de contourner un blocage.
"""

from __future__ import annotations

import os

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "fr-FR,fr;q=0.9"}

# mode : sitemap | sitemap_index | pagination | probe
# extracteur : dle (FrenchStream) | generique
SOURCES = {
    "frenchstream": {
        "enabled": True, "label": "FrenchStream", "pause": 3.0,
        "mirrors": ["fs26.lol", "french-stream.net", "fs27.lol"],
        "sitemap": "/sitemap.xml", "home": "/", "home_marker": "French Stream",
        "mode": "sitemap", "extracteur": "dle", "needs_browser": True,
        "include": [r"\.html$"],
        "exclude": ["xfsearch", "/user/", "/newposts/", "/statistics.html",
                    "/inscription", "/premium.php", "/hists/", "/engine/",
                    "/tags/", "/news/", "subaction=userinfo", "do=search",
                    "do=xfsearch", "print=", "/page/"],
        "player_buttons": ["Vidzy", "Voe", "Netu"],
        "mesure": 50799, "note": "sitemap 8,9 Mo, <loc> sur ancien domaine",
    },
    "franime": {
        "enabled": True, "label": "FRAnime", "pause": 3.0,
        "mirrors": ["franime.org"],          # .me/.tv interdisent les crawlers d'IA
        "sitemap": "/sitemap.xml", "home": "/", "home_marker": "FRAnime",
        "mode": "sitemap", "extracteur": "dle", "needs_browser": False,
        "include": [r"/catalogue/[^/?#]+$"],
        "exclude": ["/api/", "/catalogue?q=", "/surprise", "/auth", "/aide",
                    "/contact", "/catalogue$"],
        "player_buttons": [],
        "mesure": 1621, "note": "robots search=yes ; lecture = connexion requise",
    },
    "coflix": {
        "enabled": True, "label": "Coflix", "pause": 2.0,
        "mirrors": ["coflix.esq", "coflix.mom"],
        "sitemap": "/sitemap.xml", "home": "/", "home_marker": "Coflix",
        "mode": "sitemap_index", "extracteur": "generique", "needs_browser": False,
        "include": [r"/(film|serie|anime|drame)/[^/?#]+/?$"],
        "exclude": ["/films/?$", "/series/?$", "/animes/?$", "/collections/",
                    "/episode/", "/page/", "/wp-", "/genre/", "/acteur/"],
        "player_buttons": [],
        "selecteurs": {"titre": ["h1", ".cf-movie-title"],
                       "synopsis": [".cf-synopsis-text", ".cf-movie-synopsis-area"],
                       "episodes": [".cf-episode-item"]},
        "mesure": 15000, "crawl_delay": 10.0,
        "note": "532 sous-sitemaps mais 451 sont des épisodes exclus → ~15 000 fiches film/serie/anime ; robots Crawl-delay: 10",
    },
    "wawacity": {
        "enabled": True, "label": "Wawacity", "pause": 1.0,
        "mirrors": ["wawacity.wine", "www.wawacity.wine"],
        "sitemap": None, "home": "/", "home_marker": "Wawacity",
        "mode": "pagination", "extracteur": "generique", "needs_browser": False,
        "listing": ["/?p=films", "/?p=series", "/?p=mangas"],
        "fiche": r"\?p=(?:film|serie)&id=\d+-[^&\"']+",
        "include": [r"\?p=(?:film|serie)&id="],
        "exclude": ["?p=login", "?p=contact", "?p=aides", "?p=autres",
                    "?p=logiciels", "?p=jeux", "?p=ebooks", "?p=musiques"],
        "player_buttons": [],
        "mesure": 83000, "crawl_delay": 1.0,
        "note": "8309 pages de listing × ~10 nouvelles fiches ; robots Crawl-delay: 1 ; DDL, pas streaming",
    },
    "monstream": {
        "enabled": False, "label": "Monstream", "pause": 3.0,
        "mirrors": ["monstream.xyz", "monstream.archi", "monstream.click"],
        "sitemap": "/sitemap.xml", "home": "/", "home_marker": "Monstream",
        "mode": "probe", "extracteur": "generique", "needs_browser": True,
        "include": [r"/(film|serie)/"], "exclude": [], "player_buttons": [],
        "mesure": 0,
        "note": "DÉSACTIVÉ : Cloudflare 'Checking your browser' sur .xyz, 403 sur .cafe, timeout sur .archi",
    },
    "flemmix": {
        "enabled": False, "label": "Flemmix (ex-Wiflix)", "pause": 3.0,
        "mirrors": ["flemmix.irish", "flemmix.art", "flemmix.cam"],
        "sitemap": None, "home": "/", "home_marker": "Flemmix",
        "mode": "probe", "extracteur": "generique", "needs_browser": True,
        "include": [r"/(film|serie)/"], "exclude": [], "player_buttons": [],
        "mesure": 0,
        "note": "DÉSACTIVÉ : page JS anti-bot de 21 Ko, 2 liens, aucun sitemap (404)",
    },
    "darkiworld": {
        "enabled": False, "label": "Darkiworld", "pause": 3.0,
        "mirrors": ["darkiworld2026.com", "www-darkiworld.officiel.cc"],
        "sitemap": "/sitemap.xml", "home": "/", "home_marker": "Darkiworld",
        "mode": "probe", "extracteur": "generique", "needs_browser": False,
        "include": [r"/(film|serie)/"], "exclude": [], "player_buttons": [],
        "mesure": 0,
        "note": "DÉSACTIVÉ : HTTP 410 « Fermeture définitive » ; l'autre domaine est une page parking",
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
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def opt(cle: str, defaut):
    return os.environ.get(cle, defaut)


def actives() -> list[str]:
    """Sources activées, avec surcharge SCRAPER_ENABLE / SCRAPER_DISABLE."""
    plus = {x.strip() for x in opt("SCRAPER_ENABLE", "").split(",") if x.strip()}
    moins = {x.strip() for x in opt("SCRAPER_DISABLE", "").split(",") if x.strip()}
    return [n for n, c in SOURCES.items()
            if (c["enabled"] or n in plus) and n not in moins]


class Settings:
    def __init__(self):
        charge_env(opt("SCRAPER_ENV", "config.env"))
        self.db = opt("SCRAPER_DB", "data/index_web.sqlite3")
        self.pause = float(opt("SCRAPER_PAUSE", "3.0"))
        self.timeout = int(opt("SCRAPER_TIMEOUT", "35"))
        self.max_erreurs = int(opt("SCRAPER_MAX_ERREURS", "8"))
        self.limite = int(opt("SCRAPER_LIMIT", "0")) or None
        self.source = opt("SCRAPER_SOURCE", "") or None
        self.joueurs = opt("SCRAPER_PLAYERS", "1") != "0"
        self.sonder = opt("SCRAPER_PROBE", "0") == "1"
        self.incremental = opt("SCRAPER_INCREMENTAL", "1") != "0"
        self.ua = opt("SCRAPER_UA", USER_AGENT)
        self.log = opt("SCRAPER_LOG", "data/scraper.log")
        # 1 worker par source = 1 navigateur par domaine, jamais plusieurs sur le même.
        self.workers = int(opt("SCRAPER_WORKERS", "0")) or 0
        self.max_pages = int(opt("SCRAPER_MAX_PAGES", "0")) or 0
        self.pause_pagination = float(opt("SCRAPER_PAGINATION_PAUSE", "0.3"))
        self.checkpoint = opt("SCRAPER_CHECKPOINT", "") or None
        self.checkpoint_every = int(opt("SCRAPER_CHECKPOINT_EVERY", "100"))
        # GitHub Actions : budget de temps par job (doit rester sous les 6 h)
        self.max_minutes = float(opt("SCRAPER_MAX_MINUTES", "0")) or 0
        # Actions : ne pas reconstruire les sitemaps à chaque run (Wawacity = 2h30).
        self.sync_force = opt("SCRAPER_SYNC", "0") == "1"
        # Commande exécutée après chaque checkpoint (ex: push du DB sur data-*)
        self.checkpoint_hook = opt("SCRAPER_CHECKPOINT_HOOK", "") or None

    def clone(self, source: str) -> "Settings":
        n = Settings()
        for k, v in vars(self).items():
            setattr(n, k, v)
        n.source = source
        return n
