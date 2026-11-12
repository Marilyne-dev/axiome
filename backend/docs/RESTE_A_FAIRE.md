# AXIOME — Reste à faire (inventaire honnête)

État au fil de l'eau. Principe : rien n'est marqué « fait » sans code réel, testé.
Certaines lignes **ne peuvent pas** être terminées en interne : elles dépendent
d'un branchement externe (flux officiels, comptes déclarants, paquets système).
Elles sont livrées en **interface prête à brancher**, honnêtement étiquetées — jamais simulées.

## A. Dépendances externes (stubs honnêtes — non simulables)

| Élément | État actuel | Ce qu'il manque (externe) |
|---|---|---|
| Flux sanctions UE / OFAC / ONU | Fichier `storage/sanctions/liste.csv` + repli démo ; moteur de screening réel | Abonnement/téléchargement des listes officielles + rafraîchissement |
| Screening PPE | Démo | Source PPE réelle (fournisseur de données) |
| Transmission TRACFIN (ERMES) | Export JSON structuré + marquage manuel « transmise » | Compte déclarant TRACFIN + certificat + connecteur ERMES |
| OCR français | Fonctionne en anglais ; détection auto de langue | Paquet système `tesseract-ocr-fra` à installer |
| Veille réglementaire (flux) | Base manuelle curée + écran | Abonnement aux flux officiels (CNCC/ANC/UE) |
| Salariés fictifs (complet) | Signaux FEC livrés (auxiliaires 421) | Données paie/DSN détaillées (source externe) |

## B. Approfondissements internes (buildables — vrais restes)

- [x] Intégrer le signal **fraude-FEC** au **dossier de synthèse** — fait (résultat persisté, repris dans Excel + feuille de garde).
- [x] Détecteurs **fournisseurs fictifs / salariés fictifs (partie FEC-exploitable)** — fait : analyse des auxiliaires (concentration fournisseurs, montants exclusivement ronds, écriture unique élevée, nets identiques partagés), persistée et reprise dans le dossier de synthèse. La détection complète des salariés fictifs reste conditionnée à des données paie/DSN externes (voir bloc A).
- [x] **Fraude TVA** — fait : détecteur de cohérence TVA collectée (taux implicite vs bande plausible) sur le FEC, persisté et repris dans le dossier de synthèse.

- [~] **Localisation EN** du domaine — **choix de conception FR-first assumé** : chrome/navigation bilingues (72 clés symétriques, commutateur câblé), contenu réglementaire (NEP/ISA, en-têtes de feuilles de travail) en français par nature. La traduction écran par écran des libellés d'UI métier est un chantier itératif à la demande, pas un blocage.
- [x] Écran d'**administration cabinet/bureaux** — fait (édition cabinet + CRUD bureaux, réservé ADMIN).

## C. Durcissement production (hors périmètre fonctionnel de l'app)

- [ ] PostgreSQL éprouvé en conditions réelles (pool déjà dimensionné, compose fourni).
- [ ] Secrets managés (Vault/KMS), PITR PostgreSQL, reverse-proxy TLS, WAF.

Ces éléments sont des **prérequis de déploiement**, pas des fonctionnalités applicatives ;
les garde-fous de configuration (fail-fast, en-têtes de sécurité, sondes `/healthz`/`/readyz`)
sont déjà en place côté application.
