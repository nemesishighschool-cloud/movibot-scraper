# Base d'exemple

`index_web_sample.sqlite3` contient **230 fiches réelles** (200 FrenchStream +
30 FRAnime) indexées le 2026-11-02. Elle permet de tester immédiatement l'aperçu
sans attendre les 2 à 3 jours d'indexation :

```bash
SCRAPER_DB=sample/index_web_sample.sqlite3 .venv/bin/python -m scraper.cli status
SCRAPER_DB=sample/index_web_sample.sqlite3 .venv/bin/python -m scraper.cli preview
```

`web_probe_results.json` contient le diagnostic des 83 lecteurs de cet échantillon.
Pour repartir d'une base vierge, utilisez `SCRAPER_DB=data/index_web.sqlite3`.
