from scraper.config import Settings
from scraper.estimate import estimer


def test_estimation_4_sources_et_goulot():
    s = Settings()
    s.workers = 4
    e = estimer(s)
    assert e["sources_actives"] == 4
    assert e["total_fiches"] > 200000
    assert e["parallele_1_worker_par_source"]["jours"] < e["sequentiel_1_worker"]["jours"]
    assert e["parallele_1_worker_par_source"]["goulot"] == "frenchstream"
    assert "aucun effet" in e["gpu"]


def test_no_players_reduit_la_duree():
    s = Settings(); s.joueurs = False
    e = estimer(s)
    fs = [x for x in e["par_source"] if x["source"] == "frenchstream"][0]
    assert fs["surcout_s"] <= 1.5
    assert fs["heures"] < 100
