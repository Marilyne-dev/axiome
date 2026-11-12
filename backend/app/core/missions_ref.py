"""Typologie des missions du commissaire aux comptes.

Registre de référence (factuel) : chaque type de mission porte sa catégorie, sa base
normative/légale, la nature de l'expression (opinion, assurance, attestation, constat,
rapport), son livrable principal et une liste de diligences clés. Ce registre pilote le
cadre de la mission dans AXIOME ; il n'automatise pas à lui seul chaque mission
spécialisée (ex. calcul de parité de fusion, points de données ESRS), qui relève d'un
approfondissement ultérieur.
"""
from __future__ import annotations

# Catégories (ordre d'affichage).
CATEGORIES = [
    ("CERTIFICATION", "Certification"),
    ("DURABILITE", "Durabilité"),
    ("CONTROLE", "Contrôle"),
    ("ALERTE", "Alerte"),
    ("JUDICIAIRE", "Judiciaire"),
    ("CAPITAL", "Capital"),
    ("ASSURANCE", "Assurance"),
    ("CONTRACTUELLE", "Contractuelle"),
    ("ORGANISMES", "Organismes"),
]

# code -> définition
TYPES_MISSION = {
    # --- Certification (missions légales de base) ---
    "CERT_ANNUELS": {
        "categorie": "CERTIFICATION",
        "libelle": "Certification des comptes annuels",
        "base": "NEP 700 · art. L.823-9 C. com.",
        "nature": "Opinion (assurance raisonnable)",
        "livrable": "Rapport sur les comptes annuels",
        "dossier_complet": True,
        "diligences": [
            "Acceptation / maintien de la mission et indépendance",
            "Prise de connaissance de l'entité et de son environnement",
            "Évaluation des risques et seuils de signification (NEP 320)",
            "Appréciation du contrôle interne",
            "Contrôle des comptes par cycle (assertions)",
            "Revue des événements postérieurs et continuité (NEP 570)",
            "Formulation de l'opinion et rédaction du rapport",
        ],
    },
    "CERT_CONSOLIDES": {
        "categorie": "CERTIFICATION",
        "libelle": "Certification des comptes consolidés",
        "base": "NEP 600 · NEP 700",
        "nature": "Opinion (assurance raisonnable)",
        "livrable": "Rapport sur les comptes consolidés",
        "dossier_complet": True,
        "diligences": [
            "Définition du périmètre et scoping des composants (NEP 600)",
            "Instructions aux auditeurs des composants",
            "Contrôle des retraitements d'homogénéité et de conversion",
            "Éliminations intra-groupe et résultats internes",
            "Contrôle du goodwill et des impôts différés",
            "Partage des capitaux propres et bouclage des états consolidés",
            "Opinion sur les comptes consolidés",
        ],
    },
    # --- Durabilité (CSRD) ---
    "CSRD_ESG": {
        "categorie": "DURABILITE",
        "libelle": "Certification des informations en matière de durabilité (CSRD)",
        "base": "Directive CSRD · normes ESRS",
        "nature": "Assurance limitée (puis raisonnable)",
        "livrable": "Rapport d'assurance sur les informations de durabilité",
        "dossier_complet": False,
        "diligences": [
            "Analyse de double matérialité (impacts, risques, opportunités)",
            "Vérification du périmètre et de la gouvernance durabilité",
            "Contrôle des points de données ESRS (E, S, G)",
            "Cohérence avec les états financiers et le rapport de gestion",
            "Contrôle de la taxonomie et des indicateurs clés",
            "Conclusion d'assurance limitée",
        ],
    },
    # --- Contrôle / vérifications spécifiques ---
    "VERIF_SPEC": {
        "categorie": "CONTROLE",
        "libelle": "Vérifications spécifiques et rapport de gestion",
        "base": "art. L.823-10 C. com. · NEP « vérifications spécifiques »",
        "nature": "Constats / vérifications",
        "livrable": "Rapport contenant les vérifications spécifiques",
        "dossier_complet": False,
        "diligences": [
            "Concordance du rapport de gestion avec les comptes",
            "Informations données aux actionnaires (conventions réglementées)",
            "Égalité entre actionnaires",
            "Prises de participation et contrôle (filiales)",
            "Mentions obligatoires et informations diverses",
        ],
    },
    # --- Alerte ---
    "ALERTE": {
        "categorie": "ALERTE",
        "libelle": "Procédure d'alerte et continuité d'exploitation",
        "base": "art. L.234-1 s. C. com. · NEP 570",
        "nature": "Procédure / rapport spécial",
        "livrable": "Courriers d'alerte et rapport au président / à l'AG",
        "dossier_complet": False,
        "diligences": [
            "Identification des faits de nature à compromettre la continuité",
            "Information des dirigeants (phase 1) et suivi de la réponse",
            "Saisine des organes (phase 2) le cas échéant",
            "Information du président du tribunal (phase 3)",
            "Établissement du rapport spécial à l'assemblée",
        ],
    },
    # --- Judiciaire ---
    "REVELATION": {
        "categorie": "JUDICIAIRE",
        "libelle": "Révélation des faits délictueux",
        "base": "art. L.823-12 C. com.",
        "nature": "Obligation légale de révélation",
        "livrable": "Révélation au procureur de la République",
        "dossier_complet": False,
        "diligences": [
            "Qualification des faits (caractère délictueux, significatif, délibéré)",
            "Constitution du dossier de preuve",
            "Rédaction de la révélation au procureur",
            "Traçabilité et confidentialité",
        ],
    },
    # --- Capital (opérations) ---
    "FUSION_APPORT": {
        "categorie": "CAPITAL",
        "libelle": "Commissariat à la fusion / aux apports",
        "base": "art. L.236-10 · L.225-147 C. com.",
        "nature": "Rapport sur la valeur / la parité",
        "livrable": "Rapport du commissaire à la fusion / aux apports",
        "dossier_complet": False,
        "diligences": [
            "Contrôle de la réalité et de l'évaluation des apports",
            "Appréciation des méthodes d'évaluation retenues",
            "Contrôle du rapport d'échange (parité) et de son caractère équitable",
            "Vérification de l'absence de survalorisation",
            "Rédaction du rapport",
        ],
    },
    "TRANSFORMATION": {
        "categorie": "CAPITAL",
        "libelle": "Transformation de société",
        "base": "art. L.224-3 C. com.",
        "nature": "Rapport sur la situation",
        "livrable": "Rapport sur la situation de la société",
        "dossier_complet": False,
        "diligences": [
            "Appréciation de la valeur des biens composant l'actif",
            "Contrôle des capitaux propres au moins égaux au capital",
            "Rédaction du rapport de transformation",
        ],
    },
    "CAP_AUG_RED": {
        "categorie": "CAPITAL",
        "libelle": "Augmentation / réduction de capital",
        "base": "art. L.225-135 s. · L.225-204 C. com.",
        "nature": "Rapport spécial",
        "livrable": "Rapport spécial sur l'opération de capital",
        "dossier_complet": False,
        "diligences": [
            "Contrôle des modalités de l'opération",
            "Appréciation de la suppression éventuelle du DPS",
            "Contrôle de l'égalité des actionnaires (réduction)",
            "Rédaction du rapport spécial",
        ],
    },
    # --- Assurance ---
    "ATTEST_PART": {
        "categorie": "ASSURANCE",
        "libelle": "Attestations et certifications particulières",
        "base": "NEP « attestations » · doctrine CNCC",
        "nature": "Attestation / constat",
        "livrable": "Attestation particulière",
        "dossier_complet": False,
        "diligences": [
            "Définition précise de l'objet et des critères",
            "Collecte des éléments probants adaptés",
            "Contrôle de cohérence avec la comptabilité",
            "Rédaction de l'attestation",
        ],
    },
    # --- Contractuelle ---
    "CONTRACTUELLE": {
        "categorie": "CONTRACTUELLE",
        "libelle": "Mission d'assurance contractuelle autorisée",
        "base": "Cadre H3C · services autres que la certification",
        "nature": "Assurance contractuelle",
        "livrable": "Rapport de mission contractuelle",
        "dossier_complet": False,
        "diligences": [
            "Contrôle de compatibilité avec le mandat légal (indépendance)",
            "Définition de la lettre de mission et des critères",
            "Réalisation des diligences convenues",
            "Rédaction du rapport",
        ],
    },
    # --- Organismes (OSBL) ---
    "ORGANISMES": {
        "categorie": "ORGANISMES",
        "libelle": "Certification des comptes d'associations, fondations, etc.",
        "base": "NEP 700 · particularités OSBL / L.612-1",
        "nature": "Opinion (assurance raisonnable)",
        "livrable": "Rapport sur les comptes de l'organisme",
        "dossier_complet": True,
        "diligences": [
            "Prise en compte des spécificités OSBL (fonds dédiés, subventions)",
            "Contrôle de l'emploi des ressources et du compte d'emploi (le cas échéant)",
            "Contrôle des comptes par cycle",
            "Vérifications spécifiques propres aux OSBL",
            "Formulation de l'opinion",
        ],
    },
}

TYPE_DEFAUT = "CERT_ANNUELS"


def libelle_type(code: str) -> str:
    d = TYPES_MISSION.get(code)
    return d["libelle"] if d else code


def libelle_categorie(code: str) -> str:
    for c, lib in CATEGORIES:
        if c == code:
            return lib
    return code


def type_mission(code: str) -> dict:
    """Définition d'un type (ou celle du type par défaut si inconnu)."""
    return TYPES_MISSION.get(code, TYPES_MISSION[TYPE_DEFAUT])


def types_par_categorie() -> list[tuple[str, str, list[tuple[str, dict]]]]:
    """Retourne [(cat_code, cat_libelle, [(type_code, def), ...]), ...]."""
    out = []
    for cat_code, cat_lib in CATEGORIES:
        items = [(code, d) for code, d in TYPES_MISSION.items() if d["categorie"] == cat_code]
        out.append((cat_code, cat_lib, items))
    return out
