# Temps réel, GPU, Google Colab et parallélisme

Mesures du 2026-11-02 sur les sites eux-mêmes. Commande reproductible :
`python3 -m scraper.cli estimate`.

## 1. Ce qu'on a vraiment à scraper

| Source | État | Fiches mesurées | Comment obtenu |
|---|---|---|---|
| **FrenchStream** | ✅ actif | **50 799** | sitemap 8,9 Mo |
| **Coflix** (`coflix.esq`) | ✅ actif | **~91 415** | index de 532 sous-sitemaps × ~200 |
| **Wawacity** (`wawacity.wine`) | ✅ actif | **~100 000** | 5 098 pages de listing × ~20 fiches |
| **FRAnime** (`franime.org`) | ✅ actif | **1 621** | sitemap |
| Monstream | ❌ désactivé | 0 | Cloudflare « Checking your browser » sur `.xyz`, 403 sur `.cafe`, timeout sur `.archi` |
| Flemmix / Wiflix | ❌ désactivé | 0 | page JS anti-bot de 21 Ko, 2 liens, sitemap 404 |
| Darkiworld | ❌ désactivé | 0 | HTTP **410 « Fermeture définitive »** ; l'autre domaine est une page parking |

**Total exploitable : ~243 835 fiches.** Les 3 sources désactivées restent dans le
registre avec leurs miroirs et la raison, réactivables par
`SCRAPER_ENABLE=monstream,flemmix` dès qu'un domaine revient. On ne contourne
aucun blocage.

⚠️ `www.coflix.fr` et `coflixtv.cyou` sont des clones/SEO : le premier renvoie
vers `gupy.fr`, le second n'a que 170 URLs. Le vrai catalogue est sur `coflix.esq`.

## 2. Combien de temps

Temps unitaires **mesurés** : navigateur + 3 clics sur les onglets de lecteurs =
~5,5 s de travail par fiche pour FrenchStream ; ~0,8 s pour les sources en HTTP
simple. On ajoute la pause par source, ajustée au `robots.txt` :

| Source | Pause | Travail | Durée |
|---|---|---|---|
| FrenchStream | 3 s | 5,5 s | **119,9 h (5,0 j)** |
| Coflix | 2 s | 0,8 s | **71,1 h (3,0 j)** |
| Wawacity | 1 s (`Crawl-delay: 1`) | 0,8 s | **50,5 h (2,1 j)** |
| FRAnime | 3 s | 0,8 s | **1,7 h** |

| Organisation | Durée |
|---|---|
| **1 seul worker pour tout** (somme) | **243 h = 10,1 jours** |
| **1 worker par source, en parallèle** | **120 h = 5,0 jours** (gain ×2) |
| Idem + `--no-players` (passe catalogue seule) | **~71 h = 3,0 jours** |

**Le goulot, c'est FrenchStream** et ses clics sur les lecteurs. Ajouter des
sources ne rallonge presque rien (elles tournent en parallèle), mais n'accélère
pas FrenchStream. Le levier honnête : faire une **passe 1 catalogue** avec
`--no-players` (3 jours), puis une **passe 2 ciblée** sur les séries pour
résoudre les lecteurs.

À titre de comparaison, l'échantillon de 230 fiches avait pris 900,7 s soit
**3,92 s/fiche** sans clics ; le `run` avec clics sur 3 fiches a pris ~7,5 s/fiche
à pause 2 s. D'où les chiffres ci-dessus.

## 3. Le GPU T4 : aucun effet. Vraiment aucun.

Un T4 accélère les **multiplications de matrices** (entraînement/inférence ML).
Or le scraping fait : requêtes réseau → rendu HTML par Chrome → parsing
BeautifulSoup → écriture SQLite. Tout cela est **CPU + RAM + réseau**. Le GPU
reste à 0 % pendant tout le travail. Mettre un T4, un A100 ou huit GPU ne change
pas une seconde ces 120 heures.

Ce qui compte réellement :

| Ressource | Besoin | Colab T4 gratuit | Core 2 Duo 4 Go | VPS ~4,50 €/mois |
|---|---|---|---|---|
| CPU | 2–4 cœurs | ~2 vCPU ✅ | 2 cœurs ⚠️ | 2 vCPU ✅ |
| RAM | 1,5–2,5 Go (4 Chromium) | ~12 Go ✅ | 4 Go ⚠️ juste | 4 Go ✅ |
| Disque | ~250 Mo de base | éphémère ❌ | 300 Go ✅ | 40 Go ✅ |
| Durée de session | **120 h continues** | **~12 h max** ❌ | illimitée ✅ | illimitée ✅ |
| IP | résidentielle de préférence | IP de datacenter ❌ | résidentielle ✅ | datacenter ⚠️ |

## 4. Google Colab : utilisable, mais ce n'est pas le bon outil

Problèmes concrets :

1. **Session limitée à ~12 h** (souvent moins, déconnexion après inactivité).
   Il faut **~10 sessions** pour venir à bout des 120 h, donc relancer le
   notebook 10 fois.
2. **Disque éphémère** : tout ce qui est dans `/content` disparaît. D'où
   `SCRAPER_CHECKPOINT` qui copie la base sur Google Drive toutes les 100 fiches
   via `sqlite3.Connection.backup()`, et la reprise qui relit cette copie.
3. **IP de datacenter Google** : beaucoup de ces sites renvoient 403 ou un
   défi Cloudflare aux IP de cloud. Notre propre bac à sable (également une IP
   de datacenter) a essuyé ces 403 sur Monstream ; ce n'est pas un hasard.
4. Le **GPU est facturé en crédit** mais inutilisé : on paie une ressource qui
   ne sert pas.

Le notebook `colab/MoviBot_Scraper_Colab.ipynb` est fourni et **fonctionne** :
montage Drive, installation, clone du dépôt privé, checkpoint automatique,
reprise. Mais pour un travail de 5 jours, la solution la plus simple reste un
**petit VPS allumé en permanence** (Hetzner CX22 ~4,50 €/mois, 20 To de trafic
inclus) avec le service `systemd` fourni : une seule session, pas de
déconnexion, pas de copie de sûreté à gérer.

## 5. Le bon parallélisme

✅ **Une instance de Chrome par source** (`SCRAPER_WORKERS=4`) : chaque domaine
voit toujours une seule requête à la fois, avec sa pause. C'est ce qui fait
passer de 10,1 à 5,0 jours. Implémenté dans `scraper/daemon.py` via
`ThreadPoolExecutor`, une connexion SQLite WAL et un Chromium par worker.

❌ **Plusieurs Chrome sur le MÊME domaine** : ça diviserait le temps de
FrenchStream, mais ça revient à multiplier les requêtes sur un seul site, à
ignorer son `Crawl-delay` et à se faire bloquer. Ce n'est pas implémenté et ce
n'est pas une optimisation acceptable.

❌ **Rotation d'IP, VPN pour contourner, résolution de CAPTCHA** : exclus. Quand
un domaine meurt, le moteur bascule sur un miroir sain ou diffère la source.

## 6. Démarrer

```bash
# Test rapide, 3 fiches par source, 4 workers
SCRAPER_MAX_PAGES=2 SCRAPER_WORKERS=4 python3 -m scraper.cli run --limit 3 --pause 1

# Estimation avant de lancer
python3 -m scraper.cli estimate
python3 -m scraper.cli sources

# Production sur un VPS (5 jours, reprise automatique)
./scripts/lancer.sh          # ou sudo systemctl enable --now movibot-scraper@USER
```

## 7. Cadre

Ces sites diffusent des œuvres sans autorisation et changent de domaine sous la
pression des ayants droit. Le moteur ne collecte que des **métadonnées
publiques**, respecte les `robots.txt`, ne contourne rien et ne stocke aucun
média. Vérifiez vos droits avant toute redistribution des liens ou des flux.
