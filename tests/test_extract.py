import json

from scraper.extract import extraire, identifiants_dans_html
from scraper.players import host_depuis, url_download

FICHE = """<!doctype html><html lang="fr"><head>
<title>série The Gilded Age saison 4 en streaming complet</title>
<meta property="og:title" content="The Gilded Age - Saison 4">
<meta property="og:description" content="Un synopsis suffisamment long pour être pris en compte ici par l'extracteur.">
<script>var bidon = "Connexion requise";</script>
</head><body>
<h1>The Gilded Age - Saison 4</h1>
<div class="facts"><span class="certification">-TV-14</span> - 2022 -
  <span class="genres">Drame</span> - <span class="runtime">55 min</span></div>
<div class="fposter"><img src="https://image.tmdb.org/t/p/w500/abc.jpg"></div>
<div class="fdesc">Aux États-Unis, le Gilded Age désigne la période de prospérité qui suivit la guerre de Sécession.</div>
<div class="episodes-wrapper">
  <div class="episode-row" data-type="vf" data-num="1"></div>
  <div class="episode-row" data-type="vostfr" data-num="1"></div>
</div>
<iframe src="https://vidzy.org/embed-h54yhb6zj592.html?autoplay=1"></iframe>
</body></html>"""

ITEM = {"source": "frenchstream", "source_domain": "fs26.lol",
        "canonical_path": "/15141249-the-gilded-age-saison-4-2022.html",
        "url": "https://fs26.lol/15141249-the-gilded-age-saison-4-2022.html",
        "first_seen": "2026-11-02"}


def test_extraction_champs_cles():
    d = extraire(FICHE, ITEM)
    assert d["title"] == "The Gilded Age - Saison 4"
    assert d["kind"] == "serie"
    assert d["year"] == 2022
    assert d["season"] == 4
    assert d["duration_min"] == 55
    assert json.loads(d["genres"]) == ["Drame"]
    assert set(json.loads(d["languages"])) == {"VF", "VOSTFR"}
    assert d["episode_count"] == 2
    assert d["poster_url"].startswith("https://image.tmdb.org/")
    assert "Aux États-Unis" in d["synopsis"]
    assert d["status"] == "ok"


def test_le_texte_des_scripts_ne_pollue_pas_les_notes():
    d = extraire(FICHE, ITEM)
    # « Connexion requise » n'est que dans un <script> → ne doit pas être noté.
    assert not d["notes"] or "connexion" not in d["notes"]


def test_identifiants_lecteur_et_urls():
    ids = identifiants_dans_html(FICHE)
    assert "h54yhb6zj592" in ids
    e = "https://vidzy.org/embed-h54yhb6zj592.html"
    assert url_download(e) == "https://vidzy.org/d/h54yhb6zj592.html"
    assert host_depuis(e) == "Vidzy"
    assert url_download("https://exemple.com/autre") is None


def test_franime_titre_et_annee():
    h = """<html><head><title>you and i are polar opposites - FRAnime</title>
    <meta property="og:description" content="Regarder un animé en VF et en VOSTFR"></head>
    <body><h1>you and i are polar opposites</h1>
    <p>Animé you and i are polar opposites 2026 18 épisodes Regarder Connexion requise</p>
    </body></html>"""
    it = dict(ITEM, source="franime", source_domain="franime.org",
              canonical_path="/catalogue/you-and-i-are-polar-opposites",
              url="https://franime.org/catalogue/you-and-i-are-polar-opposites")
    d = extraire(h, it)
    assert d["kind"] == "anime"
    assert d["title"] == "You And I Are Polar Opposites"
    assert d["year"] == 2026
    assert d["episode_count"] == 18
    assert "connexion" in (d["notes"] or "")


COFLIX = """<html><head><title>Films The Fix En Streaming Complet HD | Coflix</title>
<meta property="og:title" content="Films The Fix En Streaming Complet HD | Coflix">
<meta property="og:description" content="Voir The Fix Film Complet En Ligne, regardez en version French">
<meta property="og:image" content="https://image.tmdb.org/t/p/w500/xyz.jpg"></head><body>
<h1>The Fix</h1><h1>Connexion requise</h1>
<div class="cf-synopsis-text">Un thriller psychologique tendu, porté par une enquête impossible.</div>
<div class="cf-episode-item">1</div><div class="cf-episode-item">2</div>
</body></html>"""

WAWACITY = """<html><head><title>Télécharger Fight Club gratuitement sur Wawacity</title>
<meta property="og:title" content="Télécharger Fight Club gratuitement sur Wawacity">
<meta property="og:description" content="Origine: USA | Durée: 02h19 | Réalisation: David Fincher">
<meta property="og:image" content="https://wawacity.wine/img/films/abc.webp"></head><body>
<h1>Films » Fight Club [BLURAY 4K] - MULTI (TRUEFRENCH)</h1><p>Drame Thriller VF VOSTFR</p>
<div class="wa-post-detail-list">Durée: 02h19 Année: 1999 Genre(s): Drame , Thriller</div>
</body></html>"""


def test_extracteur_generique_coflix():
    from scraper.config import SOURCES
    from scraper.extract import extraire_generique
    it = {"source": "coflix", "source_domain": "coflix.esq",
          "canonical_path": "/film/the-fix-2/", "url": "https://coflix.esq/film/the-fix-2/",
          "first_seen": "2026-11-02"}
    d = extraire_generique(COFLIX, it, SOURCES["coflix"])
    assert d["title"] == "The Fix"
    assert d["kind"] == "film"
    assert "thriller" in d["synopsis"].lower()
    assert d["poster_url"].startswith("https://image.tmdb.org/")
    assert d["episode_count"] == 2
    assert "connexion" in (d["notes"] or "")


def test_extracteur_generique_wawacity():
    from scraper.config import SOURCES
    from scraper.extract import extraire_generique
    it = {"source": "wawacity", "source_domain": "wawacity.wine",
          "canonical_path": "/?p=film&id=60676-fight-club",
          "url": "https://wawacity.wine/?p=film&id=60676-fight-club",
          "first_seen": "2026-11-02"}
    d = extraire_generique(WAWACITY, it, SOURCES["wawacity"])
    assert d["kind"] == "film"
    assert d["duration_min"] == 139
    assert d["year"] == 1999
    assert "téléchargement" in (d["notes"] or "")
