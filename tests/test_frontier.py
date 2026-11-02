from scraper.frontier import normaliser
from scraper.robots import analyser, autorisee


def test_normalisation_reeecrit_le_domaine():
    # Le sitemap FrenchStream pointe vers un ancien domaine : on garde le chemin.
    assert normaliser("https://french-stream.one/1234-mon-film.html", "fs26.lol") == (
        "https://fs26.lol/1234-mon-film.html", "/1234-mon-film.html")
    assert normaliser("https://franime.org/catalogue/naruto/", "franime.org") == (
        "https://franime.org/catalogue/naruto", "/catalogue/naruto")
    assert normaliser("https://x.fr/", "fs26.lol") == ("https://fs26.lol/", "/")


def test_robots_frenchstream():
    txt = """User-agent: *
Disallow: /engine/go.php
Disallow: /engine/ajax/
Allow: /engine/ajax/film_api.php
Allow: /engine/ajax/get_seasons.php
Disallow: /*do=search
Crawl-delay: 2
"""
    r = analyser(txt)
    assert r["crawl_delay"] == 2.0
    assert not autorisee("https://fs26.lol/engine/go.php?x=1", r)
    assert not autorisee("https://fs26.lol/engine/ajax/foo.php", r)
    # Allow plus spécifique gagne
    assert autorisee("https://fs26.lol/engine/ajax/get_seasons.php?a=1", r)
    assert autorisee("https://fs26.lol/1234-film.html", r)


def test_robots_franime_et_signaux():
    txt = """Content-Signal: search=yes,ai-train=no,use=reference
User-agent: GPTBot
Disallow: /
User-agent: *
Disallow: /api/
Disallow: /surprise
Allow: /
"""
    r = analyser(txt)
    assert any("search=yes" in s for s in r["signaux"])
    assert not autorisee("https://franime.org/api/secret", r)
    assert autorisee("https://franime.org/catalogue/naruto", r)
