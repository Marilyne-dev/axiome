# AXIOME — Architecture (Phase 0)

> Plateforme intelligente d'audit légal, de commissariat aux comptes et de conformité.
> Multi-utilisateurs · Multilingue (FR/EN) · Multi-référentiel (PCG_FR / IFRS / SYSCOHADA_OHADA) · Multi-devises (ISO 4217).

## 1. Principes directeurs

1. **Le référentiel est une dimension de la mission, jamais codé en dur.** Chaque `Mission` porte `(referentiel, pays, devise)`. Plan comptable, règles fiscales et modèles d'états sont chargés dynamiquement. Cloisonnement strict : une mission SYSCOHADA n'applique jamais une règle PCG.
2. **Aucune règle fiscale ni devise en dur.** Tables `Referentiel`, `RegleFiscale`, `Devise`, `TauxDeChange`.
3. **Sécurité par défaut.** bcrypt, JWT (access+refresh), MFA TOTP, RBAC granulaire, journal d'audit inaltérable, OWASP Top 10.
4. **Confidentialité LCB-FT absolue.** Les données TRACFIN/déclarations de soupçon sont invisibles du client et des rôles non habilités ; accès réservé au correspondant LCB-FT, chaque consultation est journalisée.
5. **Séparation des couches.** Présentation (templates/API) ⟂ logique métier (services) ⟂ données (models). Chaque module autonome, extensible vers 40-50 modules.

## 2. Stack

| Couche      | Technologie                                        |
|-------------|----------------------------------------------------|
| Backend     | FastAPI (Python 3.11+) · SQLAlchemy 2.x · Pydantic |
| BDD         | SQLite (dev) / PostgreSQL (prod)                   |
| Auth        | JWT access+refresh · MFA TOTP (pyotp) · bcrypt     |
| Frontend    | Jinja2 + CSS/JS vanilla (socle) → React possible   |
| i18n        | catalogues FR/EN · formats date/nombre/devise      |
| Devises     | pycountry → seed ISO 4217 complet                  |
| Excel/PDF   | openpyxl/pandas · reportlab/python-docx (Phase 3+) |
| IA          | API Anthropic Claude (clé en variable d'env)       |
| Asynchrone  | Celery + Redis (Phase 5+)                           |

## 3. Arborescence

```
axiome/
├── requirements.txt · .env.example · README.md
├── docs/ARCHITECTURE.md · docs/ROADMAP.md
├── app/
│   ├── main.py                 # point d'entrée FastAPI + montage routes/templates
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings, lecture .env)
│   │   ├── database.py         # engine, SessionLocal, Base, get_db
│   │   ├── security.py         # bcrypt, JWT, TOTP
│   │   └── i18n.py             # catalogues FR/EN + helper t()
│   ├── models/                 # SQLAlchemy — 1 domaine par fichier
│   │   ├── base.py             # Base + mixins (Timestamp, SoftDelete)
│   │   ├── user.py             # User, Role, Permission (+ tables d'association)
│   │   ├── cabinet.py          # Cabinet, Bureau
│   │   ├── client.py           # Groupe, Client
│   │   ├── mission.py          # Mission, Cycle
│   │   ├── referentiel.py      # Referentiel, RegleFiscale
│   │   ├── devise.py           # Devise, TauxDeChange
│   │   ├── audit.py            # WorkingPaper, Document, RiskItem, Sample,
│   │   │                       #   Confirmation, Recommendation, Threshold, AuditLog
│   │   └── lcbft.py            # DossierLCBFT, DeclarationSoupcon (confidentiel)
│   ├── schemas/                # Pydantic (I/O API)
│   ├── api/
│   │   ├── deps.py             # get_current_user, require_role, require_permission
│   │   └── routes_auth.py      # /auth : login, refresh, MFA
│   ├── db/
│   │   ├── iso4217.py          # source des devises (pycountry + repli)
│   │   ├── init_db.py          # création tables + admin + référentiels + devises
│   │   └── seed_data.py        # jeu de démo (cabinet, users, 2 clients FR/OHADA)
│   ├── templates/              # base.html, login.html, dashboard.html
│   └── static/css/axiome.css
└── tests/                      # pytest : auth, cloisonnement, devises, LCB-FT
```

## 4. Modèle de rôles (RBAC)

`ADMIN` · `ASSOCIE_SIGNATAIRE` · `AUDITEUR` · `COLLABORATEUR` · `CORRESPONDANT_LCBFT` · `CLIENT`

Les permissions sont des chaînes `domaine:action` (ex. `mission:read`, `lcbft:declare`) reliées aux rôles.
Seul `CORRESPONDANT_LCBFT` (et `ADMIN` selon politique) accède aux objets `lcbft.*`.

## 5. Cloisonnement multi-référentiel — invariant testé

Toute donnée comptable/règle est filtrée par `mission.referentiel`. Un service de contrôle
refuse d'appliquer une `RegleFiscale` dont le `referentiel` diffère de celui de la mission
(cf. `tests/test_referentiel_cloisonnement.py`).

## 6. Feuille de route des phases

Voir `docs/ROADMAP.md`. Phase 1 (ce livrable) = socle exécutable. Les 28 modules
sont ajoutés par incréments vérifiables, sans jamais casser le socle ni le cloisonnement.
