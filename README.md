# MoviBot Scraper — moteur multi-sources

Dépôt **privé**. Troisième brique du projet :

| Dépôt | Rôle |
|---|---|
| `movibot-indexer` | moteur Telegram + base de 20 906 médias |
| `movibot-stream` | serveur de lecture/téléchargement à héberger |
| **`movibot-scraper`** | **ce dépôt** : scraper multi-sites, base web `index_web.sqlite3` |

Il produit une base de **métadonnées** (titres, années, genres, saisons,
épisodes, langues, affiches, URLs de fiches et de lecteurs).
**Aucune vidéo n'est téléchargée ni stockée.**

---

## 1. Sources : 7 au registre, 4 actives

| Source | État | Fiches mesurées | Mode |
|---|---|---|---|
| FrenchStream (`fs26.lol`) | ✅ | 50 799 | sitemap + navigateur |
| Coflix (`coflix.esq`) | ✅ | ~15 000 | 532 sitemaps, 451 d'épisodes exclus |
| Wawacity (`wawacity.wine`) | ✅ | ~83 000 | pagination (8 309 pages) |
| FRAnime (`franime.org`) | ✅ | 1 621 | sitemap |
| Monstream | ❌ désactivé | — | Cloudflare / timeout |
| Flemmix (ex-Wiflix) | ❌ désactivé | — | page JS anti-bot, pas de sitemap |
| Darkiworld | ❌ désactivé | — | HTTP 410 « Fermeture définitive » |

**~150 420 fiches exploitables**, ~19,3 Go de HTML. Les sources désactivées restent configurées
avec leurs miroirs et la raison ; réactivation :
`SCRAPER_ENABLE=monstream,flemmix python3 -m scraper.cli sources`.
`python3 -m scraper.cli sources` affiche l'état de chacune.

Les domaines changent plusieurs fois par an : le moteur **teste chaque miroir
au démarrage** et bascule automatiquement. L'identité d'une fiche est son
**chemin canonique**, jamais son domaine. Aucun blocage n'est contourné.

## 2. Installation (Debian/Ubuntu 64 bits, Core 2 Duo ou VPS)

```bash
git clone https://github.com/nemesishighschool-cloud/movibot-scraper.git
cd movibot-scraper
sudo apt install python3 python3-venv python3-pip
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo .venv/bin/python -m playwright install-deps chromium   # libnspr4, libnss3…
cp config.example.env config.env
```

Chromium est indispensable pour **FrenchStream** (sinon ses fiches répondent
« Verification... »). Coflix, Wawacity et FRAnime sont en HTTP simple.

## 3. Commandes

```bash
python3 -m scraper.cli sources      # état des 7 sources
python3 -m scraper.cli estimate     # durée estimée, goulot, sessions Colab
python3 -m scraper.cli init         # crée la base
python3 -m scraper.cli sync         # teste les miroirs + remplit la frontière
python3 -m scraper.cli status       # fiches faites / restantes
python3 -m scraper.cli verify       # 0 doublon, 0 titre vide
python3 -m scraper.cli export       # exports/Media_web.csv + .xlsx
python3 -m scraper.cli probe        # diagnostique les lecteurs
python3 -m scraper.cli preview      # aperçu web (port 8090, ou SCRAPER_PREVIEW_PORT)
```

## 4. Lancer

```bash
# Test : 3 fiches par source, 4 navigateurs en parallèle
SCRAPER_MAX_PAGES=2 python3 -m scraper.cli run --limit 3 --pause 1

# Production : 1 worker par source (~5 jours)
./scripts/lancer.sh                 # nohup + reprise
# ou : sudo systemctl enable --now movibot-scraper@VOTRE_USER
```

| Option | Effet |
|---|---|
| `--limit N` | N fiches par source (test) |
| `--source coflix` | une seule source |
| `--workers 4` | **1 worker par source** (défaut = auto), jamais 2 sur le même domaine |
| `--pause 4` | force la pause (sinon : pause par source, 1 à 3 s) |
| `--no-players` | passe catalogue seule, ~2× plus rapide |
| `--max-pages 200` | borne la pagination Wawacity |
| `--probe-players` | classe chaque lecteur (`pret` / `attente` / `limite`) |

**Reprise** : chaque fiche est écrite et marquée `done` avant de passer à la
suivante. Coupure, `Ctrl+C`, domaine mort ou 8 erreurs consécutives → arrêt
propre ; relancer la même commande reprend sans doublon. Plusieurs workers
écrivent dans la même base en **WAL** avec `busy_timeout`.

**Mises à jour** : `sync` ne remet en attente que les URLs dont le `<lastmod>`
a changé.

## 5. Durée et parallélisme

`python3 -m scraper.cli estimate` donne les chiffres à jour. Mesures actuelles :

| Organisation | Durée |
|---|---|
| 1 worker pour tout | **210,7 h = 8,8 jours** |
| 1 worker par source (4) | **122,5 h = 5,1 jours** |
| + `--no-players` | **66 h = 2,75 jours** |

Le goulot est FrenchStream (119,9 h à lui seul, clics sur les onglets de
lecteurs). Coflix respecte un `Crawl-delay: 10` et la frontière Wawacity prend
2 h 32 au départ. Ajouter des sources ne ralentit presque rien puisqu'elles
tournent en parallèle. **Sur le Core 2 Duo, compte 5 à 6 jours de calendrier.**

⚠️ **Le GPU n'accélère rien** : Chrome, le parsing HTML et SQLite sont CPU/RAM/
réseau. Un T4 reste à 0 %. Voir `docs/TEMPS_ET_PARALLELISME.md`.

**Google Colab** fonctionne avec le notebook fourni
(`colab/MoviBot_Scraper_Colab.ipynb`) grâce au checkpoint Drive + reprise, mais
sa session de ~12 h impose ~10 relances et son IP de datacenter essuie des 403.
Pour 5 jours, un VPS à ~4,50 €/mois avec le service `systemd` fourni est plus
simple.

## 6. Ce que donne la base

```
source, source_domain, canonical_path, page_url, title, kind, year, season,
episode_count, languages, genres, duration_min, synopsis, poster_url,
players, embed_url, download_url, etat_lecteur, lastmod, first_seen,
last_checked, status, notes
```

Pour tester immédiatement **sans attendre la collecte**, la base d'exemple
(230 fiches) est fournie :

```bash
SCRAPER_DB=sample/index_web_sample.sqlite3 python3 -m scraper.cli preview
```

## 7. Règles respectées

- Séquentiel **par domaine**, une seule page de navigateur, pauses adaptées au
  `robots.txt` (Wawacity `Crawl-delay: 1`, FrenchStream 2 s pour Bing / 8 s Yandex).
- `robots.txt` relu à chaque `sync` ; les `Disallow` sont exclus.
- `franime.me` / `franime.tv` écartés (interdisent nommément les crawlers d'IA).
- Pas de rotation d'IP, pas de VPN de contournement, pas de résolution de
  défi Cloudflare : si un domaine est bloqué, on bascule ou on diffère.
- Journaux sans secret, aucune vidéo sur disque.

## 8. Limites

1. **Pas de fichier direct** : `embed_url` est un lecteur tiers intégrable ;
   `download_url` ouvre une page tierce (`X-Frame-Options: DENY`).
2. **FRAnime et Coflix** : catalogue seulement, lecture soumise à connexion.
   **Wawacity** : site de téléchargement direct, pas de lecteur.
3. Les domaines meurent : la reprise et le registre de miroirs sont obligatoires.
4. **Droits** : ces sites diffusent des œuvres sans autorisation. Cataloguer des
   métadonnées publiques n'autorise pas à redistribuer les œuvres.

Voir `docs/RECONNAISSANCE.md`, `docs/TEMPS_ET_PARALLELISME.md`, `SECURITE.md`.
