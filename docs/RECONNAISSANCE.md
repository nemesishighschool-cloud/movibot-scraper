# Reconnaissance réelle (mesures du 2026-11-02)

Tout ce qui suit a été observé sur les sites, pas supposé.

## FrenchStream

| | |
|---|---|
| Miroirs actifs | `fs26.lol`, `french-stream.net`, `fs27.lol` (HTML identique) |
| CMS | DLE (`/engine/`, `/xfsearch/`, `dle_js.js`) |
| Sitemap | **8,9 Mo / 50 799 URLs**, `<loc>` pointant vers l'ancien domaine `french-stream.one` |
| Fiche en HTTP simple | page « Verification... » de 1,9 Ko, vide |
| Fiche avec Chromium piloté | **210 Ko**, `og:title`, `div.facts` (`-TV-14 - 2022 - Drame - 55 min`), `div.fdesc`, `.episode-row[data-type]`, affiches TMDB |
| `robots.txt` | autorise catalogue + `film_api.php` + `get_seasons.php` ; **interdit** `go.php`, `download.php`, `/engine/ajax/`, `/*do=search`, `/*do=xfsearch`. `Crawl-delay: 2` (Bing), `8` (Yandex) |
| Lecteurs | `<iframe>` Vidzy / Voe / Netu. **Aucun `.mp4` ni `.m3u8` permanent** dans la fiche |

Le bouton « Télécharger la sélection » (`#bulk-download-btn`, dans
`/js/serie-player13.js`) construit `https://vidzy.org/d/<id>.html` (ou
`fsvid.lol/d/`, `vidl.lol/?ddl=`) et l'ouvre par `window.open('_blank')`.
Cette page renvoie `X-Frame-Options: DENY` → impossible à intégrer.

Les identifiants de lecteurs ne sont pas toujours dans le HTML : **cliquer
l'onglet Vidzy fait apparaître l'iframe**. Mesuré sur une fiche sans lecteur :
`https://vidzy.org/embed-vxumnd8obu6s.html?autoplay=1`. C'est ce que fait
`scraper/players.py`.

Sur 83 lecteurs sondés : **57 prêts** (176 Ko, 4 flux HLS, aucun
`X-Frame-Options`) et **26 en attente** (page « Chargement vidéo » avec
`totalDuration = 180`, soit ~3 minutes avant rechargement).

## FRAnime

| Domaine | Résultat |
|---|---|
| `franime.fr` | **403 Cloudflare**, y compris avec Chromium piloté |
| `franime.org` | 200, sitemap **1 632 URLs**, `Content-Signal: search=yes,ai-train=no` ✅ |
| `franime.me`, `franime.tv` | 200 mais `robots.txt` **interdit nommément les crawlers d'IA** → écartés |
| `franime.live` | page vitrine SEO, renvoie vers un autre site |
| `franime.to` | domaine en vente ; `franime.net` | erreur SSL |

Fiches `franime.org` : `h1` = titre, année, nombre d'épisodes,
mention **« Connexion requise »** pour la lecture, ni affiche ni lecteur.
Donc : **catalogue uniquement**.

## Environnement

`playwright install chromium` seul ne suffit pas sur une distribution minimale :
il manque `libnspr4.so`, `libnss3`… → `playwright install-deps chromium`.
Chromium headless validé sur ce bac à sable.

## Échantillon de référence

230 fiches (200 + 30), 0 erreur, 0 doublon, 900,7 s soit **3,92 s/fiche**.
Titre/synopsis/langues 100 %, année 87,8 %, genres 85,2 %, affiche 87 %,
lecteurs 36,1 % avant clic sur les onglets.
Projection pour ~52 400 fiches : **~57 heures**.

Les rapports détaillés restent dans les dépôts frères
(`RAPPORT_ECHANTILLON_WEB.md`, `TEST_LECTURE_WEB.md`, `CE_QUON_OBTIENDRA.md`).
