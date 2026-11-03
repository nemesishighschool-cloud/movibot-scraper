# Sécurité et cadre d'utilisation — DÉPÔT PUBLIC

Ce dépôt est **public** afin de bénéficier des **minutes GitHub Actions
illimitées**. Conséquence : code, échantillons, branches `data-*` et artefacts
sont lisibles et téléchargeables par n'importe qui.

## Ce qu'il n'y a PAS ici

- ❌ Aucun identifiant Telegram, aucun `SESSION_STRING`, aucun token, aucun
  mot de passe. `config.env` est ignoré par Git et ne contient que des réglages.
- ❌ Aucun fichier vidéo, aucun média stocké.
- ✅ Le `GITHUB_TOKEN` utilisé par les workflows reste dans les secrets
  chiffrés de GitHub Actions, jamais dans un fichier ni un artefact.

**Les deux autres dépôts (`movibot-indexer`, `movibot-stream`) contiennent
`config.env` avec la session Telegram et DOIVENT RESTER PRIVÉS.** Ne les
rendez jamais publics.

## Risques assumés en passant en public

1. **Exposition du contenu** : le scraper, `sample/index_web_sample.sqlite3`
   (230 fiches avec des URLs de lecteurs tiers) et les bases `data-*` sont des
   métadonnées de sites de diffusion non autorisée. Cela peut déclencher une
   **notification DMCA** ou une suspension du dépôt par GitHub.
2. **Artefacts publics** : tout le monde peut télécharger
   `movibot-base-complete`. N'y ajoutez jamais de secret, de jeton ni de donnée
   personnelle.
3. **Conditions d'usage GitHub Actions** : le scraping courtois et planifié est
   admis ; « submerger un site tiers », contourner des contrôles d'accès ou
   fournir un service de scraping à des tiers ne l'est pas. Le moteur :
   - lit et respecte les `robots.txt` et les `Crawl-delay` (Coflix 10 s,
     Wawacity 1 s) ;
   - ne lance **qu'un seul worker par domaine** ;
   - ne fait ni rotation d'IP, ni VPN de contournement, ni résolution de
     défi Cloudflare ; si un domaine est bloqué, il bascule sur un miroir sain
     ou diffère la source proprement.
4. **Droits d'auteur** : indexer des métadonnées publiques n'autorise pas à
   redistribuer les œuvres ni à diffuser les flux depuis votre application.
   Vérifiez le cadre juridique avant toute mise en ligne.
5. **Révoquez les tokens personnels** utilisés pour l'administration une fois
   les workflows en place ; le `GITHUB_TOKEN` d'Actions est automatique et
   expire à la fin du job.

## Si le dépôt doit repasser en privé

Les minutes retombent à **2 000/mois** sur le plan Free, soit ~7 mois pour la
charge complète de 12 641 minutes. Réduisez alors `--max-minutes`, espacez le
`cron`, ou passez sur un runner auto-hébergé (5 jours de job autorisés, mais
cela réintroduit une machine à maintenir).
