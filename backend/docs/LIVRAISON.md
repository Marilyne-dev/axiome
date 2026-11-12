# AXIOME — Livraison

Plateforme d'audit légal / commissariat aux comptes (FastAPI + SQLAlchemy + Jinja2).

## Démarrer

```bash
pip install -r requirements.txt
cp .env.example .env
python -m app.db.seed_data          # cabinet, clients et utilisateurs de démonstration
uvicorn app.main:app --reload       # http://127.0.0.1:8000
```

Comptes de démonstration (mot de passe entre parenthèses) : `admin@axiome.app` (`Admin!ChangeMe2026`),
`associe@axiome.app` (`Associe!2026`), `lcbft@axiome.app` (`Lcbft!2026`), `portail@axiome.app` (`Portail!2026`).

## Qualité (à la racine du projet)

```bash
python -m pytest -q     # 170 tests
ruff check app tests    # 0 anomalie
alembic upgrade head && alembic check   # 11 migrations linéaires, aucun drift
```

## Chaîne d'audit de bout en bout (vérifiée)

Import **FEC (DGFiP)** ou balance Datayoyo → classification automatique compte→cycle (PCG, éditable via
l'écran de reclassement) → **contrôles arithmétiques** (équilibre, bouclage, doublons) → **feuilles maîtresses
par cycle** → **détection de fraude sur écritures** (Benford, structuration/smurfing, window dressing, cohérence
TVA, tiers fournisseurs/salariés fictifs) consolidée en **indicateur de vigilance NEP 240** → **dossier de
synthèse Excel** + **feuille de garde Word/PDF**. Tous les signaux de fraude sont explicitement *non probants*
et requièrent le jugement de l'auditeur.

Un jeu d'exemple est fourni (voir les fichiers présentés) : `demo.fec.txt` (FEC réaliste, 51 écritures),
`dossier_synthese.xlsx`, `feuille_de_garde.docx` / `.pdf`.

## Modules couverts

Acceptation & lettre de mission, planification, import balance/FEC, analyse financière, seuils, revue
analytique (NEP 520), cartographie des risques, contrôle interne (COSO), programmes d'audit, feuilles de
travail (rapprochement, balance âgée, cadrage DSN, TVA), échantillonnage (NEP 530), confirmations externes
(NEP 505), détection de fraude (NEP 240), GED + OCR, génération Word/PDF/Excel, tableau de bord, portail
client, veille, éditions ISQM, administration cabinet, LCB-FT (classification, KYC/KYB, screening, TRACFIN).

## Périmètre non simulé (dépendances externes — voir `RESTE_A_FAIRE.md`)

Listes de sanctions et PPE officielles, transmission ERMES/TRACFIN, pack OCR français (`tesseract-ocr-fra`),
flux de veille officiels, données paie/DSN pour la détection *complète* des salariés fictifs. Ces points sont
livrés en interfaces prêtes à brancher, jamais falsifiées. Le durcissement production (Vault, PITR, TLS/WAF)
relève du déploiement, pas de l'application.

## Architecture deux espaces (livrée)

**1. Espace cabinet** (les clients d'AXIOME = cabinets d'audit)
- Compte **admin CAC** (rôle ADMIN) : contrôle son cabinet, gère ses **collaborateurs**
  (écran `/vue/administration` → section Collaborateurs : créer/activer/désactiver,
  rôles AUDITEUR/COLLABORATEUR/ASSOCIE_SIGNATAIRE/CORRESPONDANT_LCBFT — jamais SUPERADMIN).
- **Collaborateurs** : accès limité selon leur rôle.
- **Cloisonnement multi-tenant** : missions et clients filtrés par cabinet (un cabinet ne
  voit jamais les données d'un autre). Login bloqué si le cabinet est suspendu.

**2. Console éditeur** (nous = éditeur AXIOME)
- Nouveau rôle **SUPERADMIN** (compte `editeur@axiome.app`, sans cabinet).
- Écran `/console` : liste de **tous les cabinets** (comptes/entités/missions, actif/suspendu),
  **création cabinet + son CAC**, **suspension/réactivation** (bloque l'accès des utilisateurs),
  statistiques globales. Contrôle total de la plateforme.

**Routage login** : SUPERADMIN → `/console` · CLIENT (portail entité auditée) → `/portail` ·
sinon → `/dashboard`.

**Confidentialité** : le module LCB-FT/TRACFIN reste réservé au correspondant habilité —
**aucune dérogation**, même pour l'éditeur.

**« Fonctionnel »** : vraies routes/auth/données (testées). Les captures HTML sont des aperçus
statiques (formulaires neutralisés) ; l'interactivité réelle nécessite de lancer l'app
(`uvicorn app.main:app`).
