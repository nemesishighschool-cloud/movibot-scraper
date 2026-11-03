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


def test_normalisation_avec_query_wawacity():
    # Les fiches Wawacity sont des query strings sur "/" : il faut les garder.
    assert normaliser("https://wawacity.wine/?p=film&id=60676-fight-club",
                      "wawacity.wine", garder_query=True) == (
        "https://wawacity.wine/?p=film&id=60676-fight-club",
        "/?p=film&id=60676-fight-club")


def test_registre_des_sources():
    from scraper.config import SOURCES, actives
    assert "frenchstream" in actives() and "coflix" in actives()
    assert "wawacity" in actives() and "franime" in actives()
    # Sources mortes ou protégées : présentes mais désactivées, avec une raison.
    for n in ["monstream", "flemmix", "darkiworld"]:
        assert n not in actives()
        assert "DÉSACTIVÉ" in SOURCES[n]["note"]
    assert SOURCES["coflix"]["mode"] == "sitemap_index"
    assert SOURCES["wawacity"]["mode"] == "pagination"


def test_urls_sitemap_index_replis(monkeypatch):
    """Si /sitemap.xml échoue, on essaie les autres chemins connus."""
    from scraper import frontier
    appels = []
    index_xml = ('<?xml version="1.0"?><sitemapindex><sitemap>'
                 '<loc>https://example.org/movies-sitemap1.xml</loc>'
                 '</sitemap></sitemapindex>')
    enfant = ('<?xml version="1.0"?><urlset><url>'
              '<loc>https://example.org/film/test/</loc>'
              '<lastmod>2026-11-02</lastmod></url></urlset>')

    def faux_get(url, timeout=40, **kw):
        appels.append(url)
        if url.endswith('sitemap.xml'):
            return 403, ""
        if url.endswith('sitemap_index.xml'):
            return 200, index_xml
        return 200, enfant

    monkeypatch.setattr(frontier, "get", faux_get)
    out = frontier.urls_sitemap("example.org", "/sitemap.xml", index=True)
    assert out == [("https://example.org/film/test/", "2026-11-02")]
    assert any("sitemap_index.xml" in u for u in appels)


def test_get_reessaye_avant_dabandonner(monkeypatch):
    """Un 403 ponctuel est réessayé, sans rotation d'IP ni contournement."""
    import urllib.request
    from scraper import frontier
    compteur = {"n": 0}

    class Reponse:
        status = 200
        def read(self, _): return b"ok"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def faux_urlopen(req, timeout=None):
        compteur["n"] += 1
        if compteur["n"] < 3:
            raise OSError("403 simulé")
        return Reponse()

    monkeypatch.setattr(urllib.request, "urlopen", faux_urlopen)
    monkeypatch.setattr(frontier.time, "sleep", lambda _: None)
    code, corps = frontier.get("https://example.org/", 5)
    assert code == 200 and corps == "ok" and compteur["n"] == 3


def test_miroir_actif_essaie_tous_les_miroirs(monkeypatch):
    from scraper import frontier
    def faux(url, timeout=25, **kw):
        if "mort.example" in url:
            return 0, ""
        return 200, "<html><title>Coflix</title></html>"
    monkeypatch.setattr(frontier, "get", faux)
    cfg = {"mirrors": ["mort.example", "bon.example"], "home": "/",
           "home_marker": "Coflix"}
    assert frontier.miroir_actif(cfg) == "bon.example"


def test_preparer_bascule_si_sitemap_vide(monkeypatch, tmp_path):
    """Un miroir sain mais au sitemap vide ne doit pas être retenu."""
    from scraper import daemon, storage
    c = storage.ouvrir(str(tmp_path / "t.sqlite3"))
    s = daemon.Settings()
    s.source = "coflix"
    s.sync_force = True
    s.max_pages = 1
    monkeypatch.setattr(daemon, "actives", lambda: ["coflix"])
    monkeypatch.setattr(daemon, "miroir_actif",
                        lambda cfg, timeout=25: cfg["mirrors"][0])
    monkeypatch.setattr(daemon, "telecharger", lambda *a, **k: "User-agent: *\nAllow: /")
    vu = {"n": 0}
    def faux_construire(source, cfg, domaine, *a, **k):
        vu["n"] += 1
        return [] if domaine == "coflix.esq" else [
            {"source": source, "canonical_path": "/film/test/",
             "url": f"https://{domaine}/film/test/", "lastmod": None,
             "first_seen": "2026-11-02", "status": "pending"}]
    monkeypatch.setattr(daemon, "construire", faux_construire)
    actifs, _ = daemon.preparer(c, s)
    assert actifs["coflix"] == "coflix.mom"     # bascule sur le miroir valide
    assert vu["n"] == 2
    assert c.execute("SELECT COUNT(*) FROM frontier").fetchone()[0] == 1
    c.close()
