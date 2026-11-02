# Sécurité et cadre d'utilisation

Ce dépôt est **privé**. À la différence des deux autres dépôts MoviBot, il ne
contient **aucun identifiant Telegram, aucun token, aucun mot de passe** :
`config.env` ne renferme que des réglages (pause, base, limites).

Il n'y a donc rien à révoquer ici. En revanche :

1. **Ne rendez pas ce dépôt public.** Il documente et automatise la collecte
   sur des sites de diffusion non autorisée.
2. **Ne contournez rien.** Le moteur ne fait pas de rotation d'IP, ne force pas
   les protections Cloudflare (403 sur `franime.fr` → on utilise un autre miroir
   ou on diffère), et respecte les `Disallow` des `robots.txt`.
3. **Respectez les pauses.** `SCRAPER_PAUSE=3` minimum en production ; les
   `robots.txt` demandent 2 s à Bing et 8 s à Yandex. Pas de parallélisme.
4. **Droits d'auteur.** Indexer des métadonnées publiques (titres, années,
   genres) n'autorise pas à redistribuer les œuvres. Avant d'afficher des flux
   ou des liens de téléchargement dans une application, vérifiez que vous êtes
   en droit de le faire. Les ayants droit obtiennent régulièrement des blocages
   et des saisies de domaines : les liens collectés peuvent mourir du jour au
   lendemain.
5. **Pas de vidéo stockée.** Le moteur ne télécharge que du HTML de fiche et,
   sur option, le petit HTML de diagnostic du lecteur. Aucun octet de média
   n'est écrit sur disque.
6. **Journaux.** `data/scraper.log` ne contient que des chemins et des codes
   d'erreur, jamais de secret.
