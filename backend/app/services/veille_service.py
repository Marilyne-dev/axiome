"""Service de veille réglementaire : liste, création, marquage lu, amorçage."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.veille import VeilleReglementaire

# Jeu de référence stable (illustratif, non exhaustif, sans dates fabriquées).
# Sert d'amorçage ; la veille réelle est alimentable manuellement ou via connecteurs.
_REFERENCE = [
    {
        "titre": "Prise en compte du risque de fraude dans l'audit",
        "source": "CNCC", "referentiel": "PCG_FR", "reference": "NEP 240",
        "impact": "fort", "url": "https://www.cncc.fr",
        "resume": "Obligations du commissaire aux comptes en matière d'identification et de "
                  "réponse au risque de fraude (attitude d'esprit critique, procédures spécifiques).",
    },
    {
        "titre": "Continuité d'exploitation",
        "source": "CNCC", "referentiel": "PCG_FR", "reference": "NEP 570",
        "impact": "fort", "url": "https://www.cncc.fr",
        "resume": "Appréciation par l'auditeur de la capacité de l'entité à poursuivre son "
                  "exploitation et incidences sur le rapport.",
    },
    {
        "titre": "Audit des états financiers d'un groupe (norme révisée)",
        "source": "IAASB", "referentiel": "IFRS", "reference": "ISA 600",
        "impact": "fort", "url": "https://www.iaasb.org",
        "resume": "Démarche d'audit de groupe : périmètre, composants, travaux de l'auditeur du "
                  "groupe et communication avec les auditeurs de composants.",
    },
    {
        "titre": "Gestion de la qualité au niveau du cabinet",
        "source": "IAASB", "referentiel": "TRANSVERSE", "reference": "ISQM 1",
        "impact": "moyen", "url": "https://www.iaasb.org",
        "resume": "Dispositif de gestion de la qualité fondé sur les risques au niveau du cabinet "
                  "(gouvernance, ressources, réalisation des missions, suivi et remédiation).",
    },
    {
        "titre": "Acte uniforme relatif au droit comptable et à l'information financière",
        "source": "OHADA", "referentiel": "SYSCOHADA_OHADA", "reference": "AUDCIF / SYSCOHADA révisé",
        "impact": "moyen", "url": "https://www.ohada.org",
        "resume": "Cadre comptable applicable dans l'espace OHADA (SYSCOHADA révisé) : états "
                  "financiers, plan de comptes, dispositif comptable et informations en annexe.",
    },
]


def lister(db: Session, referentiel: str | None = None) -> list[VeilleReglementaire]:
    q = db.query(VeilleReglementaire)
    if referentiel and referentiel != "TOUS":
        q = q.filter(VeilleReglementaire.referentiel.in_([referentiel, "TRANSVERSE"]))
    return q.order_by(VeilleReglementaire.lu, VeilleReglementaire.id.desc()).all()


def creer(db: Session, **champs) -> VeilleReglementaire:
    v = VeilleReglementaire(**champs)
    db.add(v); db.commit(); db.refresh(v)
    return v


def marquer_lu(db: Session, veille_id: int, lu: bool = True) -> None:
    v = db.get(VeilleReglementaire, veille_id)
    if v:
        v.lu = lu
        db.commit()


def amorcer(db: Session) -> int:
    """Insère le jeu de référence si la table est vide (idempotent)."""
    if db.query(VeilleReglementaire).first():
        return 0
    for e in _REFERENCE:
        db.add(VeilleReglementaire(**e))
    db.commit()
    return len(_REFERENCE)
