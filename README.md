# MoviBot Scraper — moteur multi-sources piloté par GitHub Actions

**Dépôt PUBLIC** : c'est ce qui donne les **minutes GitHub Actions illimitées**
(12 641 min de runner nécessaires, soit ~7 mois de quota en privé).

| Dépôt | Rôle | Visibilité |
|---|---|---|
| `movibot-indexer` | moteur Telegram + base des 20 906 médias | 🔒 privé (`config.env`) |
| `movibot-stream` | serveur de lecture/téléchargement | 🔒 privé (`config.env`) |
| **`movibot-scraper`** | **ce dépôt : scraping multi-sites** | 🌍 **public** |

Il produit une base de **métadonnées** (titres, années, genres, saisons,
épisodes, langues, affiches, URLs de fiches et de lecteurs).
**Aucune vidéo n'est téléchargée ni stockée.**

---

## 1. Démarrer : rien à installer chez soi

Le premier run démarre **automatiquement** au push de `.github/workflows/scrape.yml`.
Sinon : **Actions → « MoviBot — scrape » → Run workflow**.

Le `schedule` (`0 */6 * * *`) enchaîne ensuite les runs tout seul. Chaque run
restaure la base, avance ~5 h, republie son état et s'arrête proprement avant
la limite des 6 h. **Aucune machine à laisser allumée.**

| Workflow | Fréquence | Rôle |
|---|---|---|
| `scrape.yml` | toutes les 3 h + enchaînement automatique | 4 jobs matriciels (1 par source) |
| `chain.yml` | **à la fin de chaque run** | relance le run suivant tant qu il reste des fiches |
| `export.yml` | après chaque scrape + quotidien | fusionne les 4 bases → CSV/XLSX/artefact |
| `refresh.yml` | lundi 03:00 UTC | relit les sitemaps, ne remet en attente que les `<lastmod>` modifiés |

👉 Tout le détail, les limites et les risques : **`docs/GITHUB_ACTIONS.md`**.

## 2. Combien de temps / combien d'Actions

`python3 -m scraper.cli estimate` → section `github_actions`.

| Scénario | Runs | Jobs | Minutes runner | Calendrier |
|---|---|---|---|---|
| Normal (mesuré) | **38** | 58 | 16 609 | **≈ 8 jours** |
| `no_players=true` | **13** | 33 | 9 244 | **≈ 2,7 jours** |

Coût : **0 €** sur dépôt public. Le goulot est FrenchStream : **13,2 s/fiche mesurés en CI** (clics sur les 3 lecteurs), soit 186 h de scrape pur → 38 runs de 5 h.

**« Temps réel »** : les artefacts `upload-artifact@v4` sont **immuables** et
publiés en fin de job (~5 h), ce n'est pas un flux continu. Le canal réellement
continu, ce sont les **branches `data-<source>`** poussées toutes les 200 fiches
(~25 min) : la base y est téléchargeable à tout moment. La base fusionnée, elle,
est republiée après chaque run (~6 h).

## 3. Sources : 7 au registre, 4 actives

| Source | État | Fiches retenues | Mode |
|---|---|---|---|
| FrenchStream (`fs26.lol`) | ✅ | 50 799 | sitemap + navigateur |
| Wawacity (`wawacity.wine`) | ✅ | ~83 000 | pagination (8 309 pages) |
| Coflix (`coflix.esq`) | ✅ | ~15 000 | index de 532 sitemaps, `Crawl-delay: 10` |
| FRAnime (`franime.org`) | ✅ | 1 621 | sitemap |
| Monstream | ❌ | — | Cloudflare / 403 / timeout |
| Flemmix (ex-Wiflix) | ❌ | — | page JS anti-bot, pas de sitemap |
| Darkiworld | ❌ | — | HTTP 410 « Fermeture définitive » |

**~150 420 fiches**, ~19,3 Go de HTML. Les sources désactivées restent
configurées avec leurs miroirs et la raison ; réactivation :
`SCRAPER_ENABLE=monstream,flemmix`. `python3 -m scraper.cli sources` affiche
l'état de chacune. Aucun blocage n'est contourné.

## 4. Commandes (pour développer en local)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo .venv/bin/python -m playwright install-deps chromium  # FrenchStream seulement
cp config.example.env config.env

python3 -m scraper.cli sources       # état des 7 sources
python3 -m scraper.cli estimate      # runs / jobs / minutes / coût
python3 -m scraper.cli init
python3 -m scraper.cli sync          # frontière (SCRAPER_SYNC=1 pour forcer)
python3 -m scraper.cli status
python3 -m scraper.cli verify        # 0 doublon, 0 titre vide
python3 -m scraper.cli export        # exports/Media_web.csv + .xlsx
python3 -m scraper.cli probe         # diagnostic des lecteurs
python3 -m scraper.cli preview       # aperçu web local

# Test local : 3 fiches par source, 4 workers
SCRAPER_MAX_PAGES=2 python3 -m scraper.cli run --limit 3 --pause 1
# Équivalent d'un job Actions
SCRAPER_SOURCE=coflix python3 -m scraper.cli run --max-minutes 5
```

Options de `run` : `--limit`, `--source`, `--workers`, `--pause`,
`--max-minutes`, `--max-pages`, `--no-players`, `--probe-players`.

## 5. Reprise et robustesse

- Chaque fiche est écrite et marquée `done` **avant** de passer à la suivante →
  coupure à 6 h, panne ou 8 erreurs consécutives : le run suivant reprend sans
  doublon.
- La frontière n'est reconstruite que si elle est vide ou `SCRAPER_SYNC=1` :
  sinon Wawacity repaierait 2 h 30 de pagination à chaque run.
- 4 jobs = 4 domaines différents, WAL + `busy_timeout` pour les écritures.
- Registre de miroirs testé à chaque run ; l'identité d'une fiche est son
  **chemin canonique**, jamais son domaine.

## 6. Ce que donne la base

```
source, source_domain, canonical_path, page_url, title, kind, year, season,
episode_count, languages, genres, duration_min, synopsis, poster_url,
players, embed_url, download_url, etat_lecteur, lastmod, first_seen,
last_checked, status, notes
```

Base d'exemple fournie pour tester sans attendre :
`SCRAPER_DB=sample/index_web_sample.sqlite3 python3 -m scraper.cli preview`.

## 7. Règles respectées

- Séquentiel **par domaine**, une seule page de navigateur, pauses conformes aux
  `robots.txt` (Coflix 10 s, Wawacity 1 s, FrenchStream 2 s Bing / 8 s Yandex).
- `franime.me` / `franime.tv` écartés (interdisent nommément les crawlers d'IA).
- Pas de rotation d'IP, pas de VPN de contournement, pas de résolution de défi
  Cloudflare.
- Journaux sans secret, aucune vidéo sur disque.

## 8. Limites et cadre

1. **Pas de fichier direct** : `embed_url` est un lecteur tiers intégrable ;
   `download_url` ouvre une page tierce (`X-Frame-Options: DENY`).
2. **FRAnime et Coflix** : catalogue seulement (connexion requise). **Wawacity** :
   téléchargement direct, pas de lecteur.
3. **GPU : aucun effet** — Chrome, le parsing HTML et SQLite sont CPU/RAM/réseau.
4. **Dépôt public** = code, échantillons et artefacts visibles par tous → risque
   DMCA. Voir `SECURITE.md` et `docs/GITHUB_ACTIONS.md` §7.
5. Ces sites diffusent des œuvres sans autorisation : vérifiez vos droits avant
   toute redistribution des liens ou des flux.
