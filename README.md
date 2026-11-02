# MoviBot Scraper — moteur d'indexation FrenchStream / FRAnime

Dépôt **privé**. Troisième brique du projet :

| Dépôt | Rôle |
|---|---|
| `movibot-indexer` | moteur Telegram + base de 20 906 médias |
| `movibot-stream` | serveur de lecture/téléchargement à héberger |
| **`movibot-scraper`** | **ce dépôt** : scraper web, base `index_web.sqlite3` |

Il produit une base de **métadonnées** (titres, années, genres, saisons,
épisodes, langues, affiches, URLs de fiches et de lecteurs).
**Aucune vidéo n'est téléchargée ni stockée.**

---

## 1. Installation (machine Core 2 Duo, Debian/Ubuntu 64 bits)

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

Le navigateur piloté est **indispensable pour FrenchStream** (sinon ses fiches
répondent « Verification... » au lieu du contenu). FRAnime se lit en HTTP simple.

## 2. Vérifier la machine et les sources

```bash
.venv/bin/python -m scraper.cli init       # crée la base
.venv/bin/python -m scraper.cli sync       # teste les miroirs + lit les sitemaps
.venv/bin/python -m scraper.cli status     # combien de fiches en attente
```

`sync` télécharge les sitemaps (50 799 URLs FrenchStream + ~1 600 FRAnime),
**réécrit l'hôte** vers le miroir actif, filtre avec `robots.txt`, déduplique par
chemin canonique et remplit la table `frontier`.

## 3. Lancer l'indexation

```bash
# Échantillon conseillé pour commencer
.venv/bin/python -m scraper.cli run --limit 200 --pause 3

# Puis la base complète, en tâche de fond (2 à 3 jours)
nohup .venv/bin/python -m scraper.cli run --pause 4 > data/scraper.log 2>&1 &
tail -f data/scraper.log
```

Options utiles :

| Option | Effet |
|---|---|
| `--limit N` | ne traiter que N fiches (test) |
| `--source frenchstream` / `franime` | une seule source |
| `--pause 4` | secondes entre deux fiches (défaut 3) |
| `--no-players` | ne pas cliquer les onglets de lecteurs |
| `--probe-players` | tester chaque lecteur (`pret` / `attente` / `limite`) |

**Reprise** : chaque fiche est écrite et marquée `done` avant de passer à la
suivante. Une coupure, un `Ctrl+C`, un domaine qui meurt ou 8 erreurs
consécutives arrêtent proprement ; **relancer la même commande reprend là où ça
s'était arrêté**, sans doublon.

**Mises à jour** : `sync` ne remet en attente que les URLs dont le `<lastmod>`
du sitemap a changé → quelques minutes par jour au lieu de 3 jours.

## 4. Contrôler et exporter

```bash
.venv/bin/python -m scraper.cli verify     # 0 doublon, 0 titre vide
.venv/bin/python -m scraper.cli probe      # diagnostique tous les lecteurs
.venv/bin/python -m scraper.cli export     # exports/Media_web.csv + .xlsx
.venv/bin/python -m scraper.cli preview    # aperçu web sur le port 8090
# Si le port est occupé : SCRAPER_PREVIEW_PORT=8091 ... preview
```

Pour essayer tout de suite **sans attendre l'indexation**, la base d'exemple
(230 fiches) est fournie :

```bash
SCRAPER_DB=sample/index_web_sample.sqlite3 .venv/bin/python -m scraper.cli preview
```

## 5. Ce que donne la base

```
source, source_domain, canonical_path, page_url, title, kind, year, season,
episode_count, languages, genres, duration_min, synopsis, poster_url,
players, embed_url, download_url, etat_lecteur, lastmod, first_seen,
last_checked, status, notes
```

Sur l'échantillon de 230 fiches : titre/synopsis/langues 100 %, année 88 %,
genres 85 %, affiche 87 %. Les lecteurs sont résolus en **cliquant les onglets
Vidzy/Voe/Netu** dans le navigateur (ils ne sont pas toujours dans le HTML).
Le champ `etat_lecteur` vaut `pret` (vidéo immédiate) ou `attente` (page de
chargement d'environ 180 secondes imposée par le site source).

## 6. Règles respectées

- **Séquentiel**, une seule page de navigateur, pause de 3 à 5 s, aucun
  parallélisme agressif, pas de rotation d'IP.
- `robots.txt` relu à chaque `sync` : les chemins `Disallow` sont exclus
  (`go.php`, `download.php`, `/engine/ajax/`, recherche interne, `/api/`…).
- `franime.me` et `franime.tv` sont **écartés** : leur `robots.txt` interdit
  nommément les crawlers d'IA. `franime.org` déclare `search=yes`.
- `franime.fr` renvoie 403 Cloudflare : on ne tente pas de le contourner, on
  utilise un autre miroir ou on diffère.
- **Registre de miroirs** : les domaines changent plusieurs fois par an ; au
  démarrage on teste chaque miroir et on bascule automatiquement. L'identité
  d'une fiche est son **chemin canonique**, jamais son domaine.
- Journaux sans secret, aucune vidéo sur disque.

## 7. Limites à connaître

1. **Pas de fichier direct** : les fiches ne contiennent aucun `.mp4` permanent.
   `embed_url` est un lecteur tiers intégrable dans un `<iframe>` ;
   `download_url` ouvre une page tierce avec `X-Frame-Options: DENY`.
2. **FRAnime** : catalogue uniquement — la lecture demande une connexion chez
   eux, et leurs fiches n'ont ni affiche ni lecteur.
3. **Durée** : ~52 400 fiches × ~4 s ≈ **57 heures** de fonctionnement continu.
4. **Droits** : ce sont des sites de diffusion non autorisée. Cataloguer des
   métadonnées publiques est une chose ; diffuser leurs flux depuis votre appli
   en est une autre. Vérifiez le cadre juridique avant toute mise en ligne.

Voir `docs/RECONNAISSANCE.md` pour les mesures réelles et `SECURITE.md`.
