# Temps réel sur un Core 2 Duo seul, GPU, Colab et parallélisme

Mesures du 2026-11-02 sur les sites eux-mêmes. Commande reproductible :
`python3 -m scraper.cli estimate`.

---

## 0. Réponse courte : machine Core 2 Duo, sans arrêt

| Ce que tu lances | Durée | Jours |
|---|---|---|
| `./scripts/lancer.sh` (défaut, **1 worker par source**) | **122,5 h** | **≈ 5,1 jours** |
| Un seul worker pour TOUT (`--workers 1`) | 210,7 h | ≈ 8,8 jours |
| `--workers 4 --no-players` (passe catalogue seule) | **66,0 h** | **≈ 2,75 jours** |

Le chiffre à retenir : **environ 5 jours et 2 heures non-stop** avec la
configuration normale. Le GPU n'y change rien (§3).

Compris dans ces 5,1 jours : **2 h 32 de préparation** au départ (sitemaps +
8 309 pages de listing Wawacity), puis les 4 sources en parallèle. Le goulot est
**FrenchStream : 119,9 h à lui seul**, à cause des clics sur les onglets de
lecteurs. Les trois autres sources finissent avant lui (Coflix 45 h, Wawacity
44 h, FRAnime 1,7 h).

⚠️ « Sans arrêt » est un idéal. En pratique, sur 5 jours : un domaine peut
mourir, un 403 peut arriver, le courant peut couper. Le moteur écrit chaque
fiche avant de passer à la suivante → **relancer reprend exactement là où c'était
arrêté**, sans doublon. Prévois plutôt **5 à 6 jours** de calendrier.

---

## 1. Ce qu'on a vraiment à scraper (chiffres corrigés)

| Source | État | Fiches retenues | Comment mesuré |
|---|---|---|---|
| **FrenchStream** | ✅ | **50 799** | sitemap 8,9 Mo |
| **Wawacity** | ✅ | **~83 000** | 8 309 pages de listing × ~10 nouvelles fiches |
| **Coflix** (`coflix.esq`) | ✅ | **~15 000** | 532 sous-sitemaps, mais **451 sont des épisodes exclus** du filtre |
| **FRAnime** (`franime.org`) | ✅ | **1 621** | sitemap |
| Monstream | ❌ | 0 | Cloudflare / 403 / timeout |
| Flemmix (ex-Wiflix) | ❌ | 0 | page JS anti-bot, sitemap 404 |
| Darkiworld | ❌ | 0 | HTTP 410 « Fermeture définitive » |

**Total : ~150 420 fiches**, ~19,3 Go de HTML à télécharger (images bloquées).

Corrections apportées après vérification :
- Coflix : l'index annonce 532 sitemaps, mais 451 contiennent des `/episode/…`
  que le filtre `include` écarte. Seuls films/séries/animes comptent → ~15 000,
  pas 91 000.
- Wawacity : `&page=N` fonctionne (les IDs changent), mais chaque page ne donne
  que ~10 nouvelles fiches ; les 33 autres liens sont une barre latérale
  commune à toutes les pages.

## 2. Détail du calcul

| Source | Pause effective | Travail / fiche | Frontière | Durée |
|---|---|---|---|---|
| FrenchStream | 3 s | 5,5 s (3 clics lecteurs) | 12 s | **119,9 h** |
| Coflix | **10 s** (`Crawl-delay: 10`) | 0,8 s | 90 s | **45,0 h** |
| Wawacity | 1 s (`Crawl-delay: 1`) | 0,8 s | **9 000 s** | **44,0 h** |
| FRAnime | 3 s | 0,8 s | 3 s | **1,7 h** |

Le `Crawl-delay: 10` de Coflix s'applique au `User-agent: *` : le moteur le
respecte, donc Coflix ne peut pas descendre sous 10 s entre deux fiches.

| Organisation | Durée |
|---|---|
| 1 worker pour tout (somme) | **210,7 h = 8,8 j** |
| 1 worker par source (4, parallèle) | **122,5 h = 5,1 j** |
| + `--no-players` | **66,0 h = 2,75 j** |

**Le levier honnête** : faire une passe 1 catalogue avec `--no-players`
(2,75 j), puis une passe 2 ciblée sur les séries pour résoudre les lecteurs.
On ne met **jamais** deux Chrome sur le même domaine pour aller plus vite.

## 3. Le GPU T4 : aucun effet. Vraiment aucun.

Un T4 accélère les multiplications de matrices (ML). Le scraping fait :
requêtes réseau → rendu HTML par Chrome → parsing BeautifulSoup → écriture
SQLite. **100 % CPU + RAM + réseau, 0 % GPU.** Un A100 ou huit GPU ne
changeraient pas une seule seconde ces 122,5 heures.

Ce qui compte sur le Core 2 Duo :

| Ressource | Besoin réel | Ton Core 2 Duo 4 Go |
|---|---|---|
| CPU | 2 cœurs, travail surtout I/O | ✅ suffisant |
| RAM | **1 seul Chromium** (~500 Mo) + 3 threads HTTP | ✅ largement (4 Go) |
| Disque | ~250 Mo de base | ✅ 300 Go |
| Réseau | ~19,3 Go sur 5 jours | ✅ ~0,4 Mo/s en moyenne |
| Allumage | 122 h continues | ⚠️ chaleur, ~10 kWh, usure d'une machine de 2007 |

Point important : **seule FrenchStream a besoin d'un navigateur**. Coflix,
Wawacity et FRAnime sont du simple HTTP. Donc « 4 workers » ne lance qu'**un**
Chrome, pas quatre : la machine de 2007 le supporte.

## 4. Google Colab : ~11 sessions de 12 h

Le notebook `colab/MoviBot_Scraper_Colab.ipynb` fonctionne (montage Drive,
checkpoint de la base toutes les 100 fiches, reprise). Mais :

1. session **~12 h** → **11 relances** pour 122,5 h ;
2. disque `/content` éphémère → d'où le checkpoint Drive ;
3. **IP de datacenter Google** → 403 fréquents sur ces sites ;
4. le GPU T4 est facturé en crédit alors qu'il ne sert à rien.

Pour 5 jours, un **VPS ~4,50 €/mois** (20 To inclus, `systemd` fourni) reste
plus simple : une seule session, pas de déconnexion.

## 5. Le bon parallélisme

✅ **Une instance de Chrome par source** (`SCRAPER_WORKERS=0` = auto, soit 4 ici) :
chaque domaine ne voit qu'une requête à la fois, avec sa pause. C'est ce qui
fait passer de 8,8 à 5,1 jours. Implémenté via `ThreadPoolExecutor`, une
connexion SQLite **WAL** par worker et un Chromium uniquement pour FrenchStream.

❌ **Plusieurs Chrome sur le MÊME domaine** : diviserait le temps de
FrenchStream mais ignorerait son `Crawl-delay` et finirait en blocage. Non
implémenté, non recommandé.

❌ Rotation d'IP, VPN de contournement, résolution de défi Cloudflare : exclus.
Si un domaine meurt, le moteur bascule sur un miroir sain ou diffère la source.

## 6. Démarrer sur le Core 2 Duo

```bash
git clone https://github.com/nemesishighschool-cloud/movibot-scraper.git
cd movibot-scraper
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m playwright install chromium
sudo .venv/bin/python -m playwright install-deps chromium
cp config.example.env config.env

# Vérifier le matériel et le temps estimé
python3 -m scraper.cli estimate
SCRAPER_MAX_PAGES=2 python3 -m scraper.cli run --limit 3 --pause 1  # test 4 sources

# Production, 5 jours, reprise automatique
./scripts/lancer.sh
# ou : sudo systemctl enable --now movibot-scraper@VOTRE_USER
```

Suivi : `tail -f data/scraper.log`, `python3 -m scraper.cli status`.

## 7. Cadre

Ces sites diffusent des œuvres sans autorisation et changent de domaine sous la
pression des ayants droit. Le moteur ne collecte que des métadonnées publiques,
respecte les `robots.txt`, ne contourne rien et ne stocke aucun média. Vérifie
tes droits avant toute redistribution des liens ou des flux.
