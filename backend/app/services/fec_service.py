"""Module 5 — Import FEC (Fichier des Écritures Comptables, DGFiP).

Le FEC est un texte délimité (tabulation ou pipe) à 18 colonnes normalisées.
On en dérive la balance générale (solde = débit − crédit par compte) et les
agrégats utiles au calcul des seuils (résultat, CA, capitaux propres).
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field

COLONNES_FEC = (
    "JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
    "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
    "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet",
    "ValidDate", "Montantdevise", "Idevise",
)


@dataclass
class LigneBalanceDTO:
    compte: str
    libelle: str
    solde: float  # débit − crédit (convention PCG)
    debit: float = 0.0
    credit: float = 0.0


@dataclass
class ResultatImportFEC:
    lignes: list[LigneBalanceDTO] = field(default_factory=list)
    nb_ecritures: int = 0
    total_debit: float = 0.0
    total_credit: float = 0.0
    # Agrégats pour les seuils
    resultat_net: float = 0.0
    chiffre_affaires: float = 0.0
    capitaux_propres: float = 0.0

    @property
    def equilibre(self) -> bool:
        """Le FEC est équilibré si Σdébit ≈ Σcrédit."""
        return abs(self.total_debit - self.total_credit) < 0.01


def _to_float(valeur: str) -> float:
    """Convertit un montant FEC ('1 234,56' ou '1234.56') en float."""
    if not valeur:
        return 0.0
    v = valeur.strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


def _to_date(valeur: str):
    """Convertit une date FEC 'AAAAMMJJ' en datetime.date (None si invalide)."""
    from datetime import date
    v = (valeur or "").strip()
    if len(v) != 8 or not v.isdigit():
        return None
    try:
        return date(int(v[:4]), int(v[4:6]), int(v[6:8]))
    except ValueError:
        return None


@dataclass
class EcritureFEC:
    date: object          # datetime.date | None
    journal: str
    compte: str
    libelle: str
    debit: float
    credit: float
    aux_num: str = ""     # CompAuxNum — tiers (fournisseur, client, salarié…)
    aux_lib: str = ""     # CompAuxLib

    @property
    def montant(self) -> float:
        """Montant de la ligne (max du débit et du crédit)."""
        return max(self.debit, self.credit)


def parser_ecritures(contenu: str) -> list[EcritureFEC]:
    """Parse un FEC au niveau écriture (une entrée par ligne comptable)."""
    contenu = contenu.lstrip("\ufeff")
    premiere = contenu.splitlines()[0] if contenu else ""
    sep = _detecter_delimiteur(premiere)
    lecteur = csv.DictReader(io.StringIO(contenu), delimiter=sep)
    ecritures: list[EcritureFEC] = []
    for row in lecteur:
        compte = (row.get("CompteNum") or "").strip()
        if not compte:
            continue
        ecritures.append(EcritureFEC(
            date=_to_date(row.get("EcritureDate", "")),
            journal=(row.get("JournalCode") or "").strip(),
            compte=compte,
            libelle=(row.get("EcritureLib") or row.get("CompteLib") or "").strip(),
            debit=_to_float(row.get("Debit", "")),
            credit=_to_float(row.get("Credit", "")),
            aux_num=(row.get("CompAuxNum") or "").strip(),
            aux_lib=(row.get("CompAuxLib") or "").strip(),
        ))
    return ecritures


def _detecter_delimiteur(entete: str) -> str:
    """Détecte le séparateur (tabulation prioritaire, sinon pipe, sinon ';')."""
    for sep in ("\t", "|", ";"):
        if sep in entete:
            return sep
    return "\t"


def parser_fec(contenu: str) -> ResultatImportFEC:
    """Parse un FEC et calcule la balance + les agrégats.

    Tolérant : accepte les colonnes dans l'ordre standard, en-tête présent.
    """
    contenu = contenu.lstrip("\ufeff")  # BOM éventuel
    premiere_ligne = contenu.splitlines()[0] if contenu else ""
    sep = _detecter_delimiteur(premiere_ligne)
    lecteur = csv.DictReader(io.StringIO(contenu), delimiter=sep)

    soldes: dict[str, float] = {}
    debits: dict[str, float] = {}
    credits: dict[str, float] = {}
    libelles: dict[str, str] = {}
    res = ResultatImportFEC()

    for row in lecteur:
        compte = (row.get("CompteNum") or "").strip()
        if not compte:
            continue
        debit = _to_float(row.get("Debit", ""))
        credit = _to_float(row.get("Credit", ""))
        soldes[compte] = soldes.get(compte, 0.0) + debit - credit
        debits[compte] = debits.get(compte, 0.0) + debit
        credits[compte] = credits.get(compte, 0.0) + credit
        libelles.setdefault(compte, (row.get("CompteLib") or "").strip())
        res.nb_ecritures += 1
        res.total_debit += debit
        res.total_credit += credit

    for compte, solde in sorted(soldes.items()):
        res.lignes.append(LigneBalanceDTO(
            compte=compte, libelle=libelles.get(compte, ""), solde=round(solde, 2),
            debit=round(debits.get(compte, 0.0), 2), credit=round(credits.get(compte, 0.0), 2)))

    # Agrégats (produits = crédit−débit ; charges = débit−crédit)
    def _somme(prefixes: tuple[str, ...], sens: str) -> float:
        total = 0.0
        for l in res.lignes:
            if l.compte.startswith(prefixes):
                total += -l.solde if sens == "credit" else l.solde
        return round(total, 2)

    charges = _somme(("6",), "debit")
    produits = _somme(("7",), "credit")
    res.resultat_net = round(produits - charges, 2)
    res.chiffre_affaires = _somme(("70",), "credit")
    res.capitaux_propres = _somme(("10", "11", "12", "13", "14"), "credit")
    return res
