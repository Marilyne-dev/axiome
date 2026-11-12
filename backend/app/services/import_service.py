"""Module 5 — Import de la balance générale (format Datayoyo 'Table_BG' ou générique).

Détecte automatiquement les colonnes par leurs en-têtes (souple, tolérant aux
variations de casse/espaces), puis crée des LigneBalance rattachées à la mission.
"""
from __future__ import annotations

import io

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.core.cycles_ref import cycle_pour_cs
from app.models.balance import LigneBalance

# Correspondances d'en-têtes tolérantes (clé interne -> fragments possibles).
_MAP = {
    "etablissement": ["codeetbt", "etablissement", "etbt"],
    "compte": ["compte", "comptenum", "numero", "n° compte", "account"],
    "compte_name": ["comptename", "compte name", "libelle compte"],
    "cs_standard": ["cs_standard", "cs standard", "cycle"],
    "solde_n": ["solde_n", "solde n", "v_gene_solde_n", "solde"],
    "solde_n1": ["solde_n_1", "solde n-1", "v_gene_solde_n_1", "solde n1"],
    "mvt_debit": ["mvt_debit", "debit", "v_gene_mvt_debit_n"],
    "mvt_credit": ["mvt_credit", "credit", "v_gene_mvt_credit_n"],
    "bilan_niv2": ["bilanniv2", "bilan niv2", "actif/passif"],
    "detail_niv1": ["detailniv1", "detail niv1"],
    "liasse": ["liasselibelle", "liasse"],
}


def _norm(h) -> str:
    return str(h or "").strip().lower().replace("[", "").replace("]", "")


def _mapper_colonnes(entetes: list) -> dict[str, int]:
    """Associe chaque clé interne à l'index de colonne le plus probable."""
    resolus: dict[str, int] = {}
    normalises = [_norm(h) for h in entetes]
    for cle, fragments in _MAP.items():
        for i, h in enumerate(normalises):
            if any(frag in h for frag in fragments):
                resolus[cle] = i
                break
    return resolus


def _num(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _split_compte(compte_name: str) -> tuple[str, str]:
    """'51202100 - Crédit agricole' -> ('51202100', 'Crédit agricole')."""
    s = str(compte_name or "").strip()
    if " - " in s:
        num, lib = s.split(" - ", 1)
        return num.strip(), lib.strip()
    return s, ""


def importer_balance(db: Session, mission_id: int, contenu_xlsx: bytes,
                     feuille: str = "Table_BG") -> dict:
    """Lit un classeur en mémoire, détecte les colonnes et insère les lignes de balance."""
    wb = load_workbook(io.BytesIO(contenu_xlsx), read_only=True, data_only=True)
    ws = wb[feuille] if feuille in wb.sheetnames else wb[wb.sheetnames[0]]

    lignes = ws.iter_rows(values_only=True)
    entetes = list(next(lignes))
    cols = _mapper_colonnes(entetes)
    if "compte" not in cols and "compte_name" not in cols:
        raise ValueError("Colonne 'compte' introuvable dans le fichier importé.")

    # Purge des lignes existantes pour cette mission (réimport idempotent).
    db.query(LigneBalance).filter_by(mission_id=mission_id).delete()

    def _cell(row: tuple, cle: str):
        i = cols.get(cle)
        return row[i] if i is not None and i < len(row) else None

    nb = 0
    for row in lignes:
        if "compte_name" in cols:
            compte, libelle = _split_compte(_cell(row, "compte_name"))
        else:
            compte, libelle = str(_cell(row, "compte") or "").strip(), ""
        if not compte:
            continue
        cs = str(_cell(row, "cs_standard") or "").strip()
        db.add(LigneBalance(
            mission_id=mission_id,
            etablissement=str(_cell(row, "etablissement") or "").strip(),
            compte=compte, libelle=libelle, cs_standard=cs,
            solde_n=_num(_cell(row, "solde_n")), solde_n1=_num(_cell(row, "solde_n1")),
            mvt_debit_n=_num(_cell(row, "mvt_debit")), mvt_credit_n=_num(_cell(row, "mvt_credit")),
            bilan_niv2=str(_cell(row, "bilan_niv2") or "").strip(),
            detail_niv1=str(_cell(row, "detail_niv1") or "").strip(),
            liasse=str(_cell(row, "liasse") or "").strip(),
        ))
        nb += 1
    wb.close()
    db.commit()

    # Répartition par cycle (aperçu)
    repartition: dict[str, int] = {}
    for lb in db.query(LigneBalance).filter_by(mission_id=mission_id).all():
        c = cycle_pour_cs(lb.cs_standard)
        repartition[c] = repartition.get(c, 0) + 1
    return {"lignes_importees": nb, "repartition_par_cycle": repartition}
