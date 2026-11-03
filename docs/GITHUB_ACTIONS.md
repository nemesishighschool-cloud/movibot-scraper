# GitHub Actions — architecture, durée et limites

Le scraping tourne **uniquement** sur GitHub Actions. Plus de Colab, plus de
machine locale, plus de VPS, plus de `nohup`/`systemd` : un `schedule` enchaîne
les runs, chaque run reprend la base là où le précédent s'est arrêté.

Reproductible : `python3 -m scraper.cli estimate` (section `github_actions`).

---

## 1. Pourquoi passer le dépôt en PUBLIC

| | Dépôt privé (Free) | **Dépôt public** |
|---|---|---|
| Minutes de runner | **2 000 / mois** | **illimitées** |
| Stockage artefacts | 500 Mo | 500 Mo inclus (identique) |
| Jobs simultanés | 20 | 20 |
| Coût | 0 € puis 0,006 €/min | **0 €** |

La charge totale est de **12 641 minutes de runner** (210,7 h). En privé il
faudrait **~7 mois** avec le quota gratuit, ou payer. En public, c'est gratuit
et sans plafond de minutes. C'est la seule raison du passage en public.

⚠️ Les deux autres dépôts (`movibot-indexer`, `movibot-stream`) contiennent
`config.env` avec la **session Telegram** : ils **restent privés**. Celui-ci ne
contient aucun secret (vérifié avant publication).

## 2. Les limites qui comptent (2026)

| Limite | Valeur | Conséquence ici |
|---|---|---|
| **Durée max d'un job** | **6 h**, coupure sans préavis | on s'arrête à **300 min** + `timeout-minutes: 350` |
| Durée max d'un workflow | 35 jours | largement suffisant |
| Jobs simultanés (Free) | 20 | 4 jobs matriciels, largement assez |
| Jobs par matrice | 256 | 4 |
| Artefacts par job | 500 | 1 par job |
| Taille d'un fichier Git | 100 Mo | base **gzip** avant push (20–40 Mo) |
| `upload-artifact` v4 | **immuable**, 1 nom = 1 upload par run | pas de flux continu → voir §4 |
| Rétention artefacts (public) | 1 à 90 jours | 2 j pour les `db-*`, 14 j pour la base complète |
| Cache Actions | 10 Go / dépôt | non utilisé (les branches `data-*` suffisent) |
| Cron minimum | 5 min | `0 */6 * * *` |
| Workflows planifiés | désactivés après 60 j d'inactivité | les pushes de checkpoint maintiennent le dépôt actif |

## 3. Combien de runs et de jobs

`estimate` donne les chiffres exacts. Avec un budget de **330 min/job** :

| Source | Minutes | Jobs de 5 h 30 |
|---|---|---|
| FrenchStream | 7 194 | **22** |
| Coflix (Crawl-delay 10) | 2 700 | 9 |
| Wawacity (+ 2 h 30 de frontière) | 2 640 | 8 |
| FRAnime | 102 | 1 |
| **Total** | **12 641** | **40 jobs** |

Les 4 sources tournent **en parallèle** dans un même run (matrice). Le nombre
de runs est donc piloté par FrenchStream : **22 workflow runs**.

| Scénario | Runs | Jobs | Minutes | Calendrier |
|---|---|---|---|---|
| Normal (avec lecteurs) | **22** | 40 | 12 641 | **≈ 121 h = 5,0 jours** |
| `--no-players` (catalogue seul) | **12** | 30 | 9 254 | **≈ 66 h = 2,75 jours** |

Les runs s'enchaînent toutes les 6 h via `schedule`. Aucune intervention
manuelle, aucun GPU, aucun crédit payé.

## 4. « Temps réel » : ce qui est vrai et ce qui ne l'est pas

**❌ Un artefact n'est pas un flux.** `actions/upload-artifact@v4` crée une
archive **immuable** quand l'étape s'exécute, c'est-à-dire **à la fin du job**
(~5 h). On ne peut pas l'alimenter en continu, et deux uploads ne peuvent pas
partager le même nom dans un même run.

**✅ Le vrai canal continu, ce sont les branches `data-*`.** Après chaque
checkpoint (200 fiches, soit **~20 à 30 min**), `scripts/gh_checkpoint.sh`
pousse la base SQLite compressée sur une branche orpheline `data-<source>` :
un seul commit forcé, donc l'historique ne gonfle pas. Chaque source a sa propre
branche → les 4 jobs ne se marchent pas dessus.

| Canal | Fréquence | Contenu |
|---|---|---|
| Branche `data-frenchstream` etc. | **toutes les ~25 min** | base SQLite gzip de la source, téléchargeable à tout moment |
| `$GITHUB_STEP_SUMMARY` | fin de job | compteurs lisibles dans l'onglet Actions |
| Artefact `db-<source>` | fin de chaque job (~5 h) | snapshot gzip de la base |
| Artefact `movibot-base-complete` | après chaque run (~6 h) | **base fusionnée + CSV + XLSX** |

Le workflow `export.yml` se déclenche sur `workflow_run` après chaque scrape :
il récupère les 4 branches, fusionne, exporte et publie l'artefact complet.
Donc la base consolidée est rafraîchie **toutes les ~6 heures**.

## 5. Architecture

```
schedule 0 */6 * * *  (ou workflow_dispatch)
        │
        ▼  matrix.source = frenchstream | coflix | wawacity | franime
   ┌───────────────────────── job (≤ 5 h 50) ─────────────────────────┐
   │ checkout → restore data-<source> → scraper --max-minutes 300      │
   │      ↳ toutes les 200 fiches : gh_checkpoint.sh → push data-*     │
   │      ↳ fin : gzip → artefact db-<source> + Step Summary           │
   └───────────────────────────────────────────────────────────────────┘
        │ workflow_run completed
        ▼
   export.yml : fetch 4 branches → merge_bases.py → CSV/XLSX
                → artefact movibot-base-complete

   refresh.yml (lundi 03:00) : SCRAPER_SYNC=1 → relit les sitemaps
                → ne remet en attente que les <lastmod> modifiés
```

**Reprise** : chaque fiche est écrite et marquée `done` avant de passer à la
suivante. Coupure à 6 h, erreur réseau, domaine mort → le run suivant
restaure `data-<source>` et continue. **0 doublon.**

**Frontière persistée** : `preparer` ne relit les sitemaps que si la table
`frontier` est vide ou si `SCRAPER_SYNC=1`. Sinon Wawacity repaierait 2 h 30
de pagination à chaque run.

## 6. Mises à jour régulières

- `scrape.yml` : toutes les 6 h, avance sur les URLs `pending`.
- `refresh.yml` : hebdomadaire, relit les sitemaps et ne remet en attente que
  les URLs dont `<lastmod>` a changé → quelques centaines de fiches, pas 150 000.
- `export.yml` : après chaque run de scrape + quotidien, republie la base
  fusionnée.
- Déclenchement manuel : Actions → « MoviBot — scrape » → *Run workflow*
  avec `sync=true` ou `no_players=true` au besoin.

## 7. Risques du dépôt public — à lire

1. **Tout est visible** : le code, `sample/index_web_sample.sqlite3` (230 fiches
   avec des URLs de lecteurs tiers) et les **artefacts téléchargeables par
   n'importe qui**. Aucun secret, mais ce sont des métadonnées de sites de
   diffusion non autorisée → risque de **notification DMCA** ou de fermeture
   du dépôt. Si ça arrive, repasser en privé réduira les minutes à 2 000/mois.
2. **Conditions d'usage GitHub** : le scraping ponctuel et courtois est admis,
   mais « submerger un site tiers », contourner des contrôles ou fournir un
   service de scraping commercial ne l'est pas. Le moteur respecte les
   `robots.txt`, les `Crawl-delay`, ne fait ni rotation d'IP ni résolution de
   défi Cloudflare, et garde **un seul worker par domaine**.
3. **IP de datacenter GitHub** : certains sites renvoient 403. Le moteur
   diffère la source au lieu de forcer.
4. **Ne jamais mettre de secret** dans `config.env`, les artefacts ou les
   branches `data-*` : sur un dépôt public, tout est lisible. Le
   `GITHUB_TOKEN` reste dans les secrets chiffrés d'Actions.
5. **Droits d'auteur** : cataloguer des métadonnées publiques n'autorise pas à
   redistribuer les œuvres.

## 8. Commandes utiles

```bash
python3 -m scraper.cli estimate          # runs, jobs, minutes, coût
python3 -m scraper.cli sources           # état des 7 sources
python3 -m scraper.cli status            # avancement local
python3 -m scraper.cli verify            # 0 doublon, 0 titre vide
```
