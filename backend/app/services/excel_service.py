"""Module 20 — Génération des tableaux Excel par cycle (gabarit Datayoyo).

Produit une Feuille Maîtresse et une feuille de travail fidèles à la structure
des dossiers Datayoyo :
  - bloc en-tête (client / exercice / collaborateur / responsable / dates de revue)
  - Feuille Maîtresse : Compte | Solde N | Solde N-1 | Variation | % | Réf. procédure
  - feuille de travail : Objectifs + Travaux à effectuer.
Variation et % sont calculés par FORMULE (zéro erreur : division protégée).
"""
from __future__ import annotations

import io
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.core.cycles_ref import CYCLES, cycle_pour_cs, libelle_cycle
from app.core.travaux_ref import OBJECTIF_GENERIQUE, travaux
from app.models.audit import Threshold
from app.models.balance import LigneBalance
from app.models.mission import Mission
from app.services import synthese_service

# --- Styles (police professionnelle, format monétaire, %) ---
_NAVY = "0B2545"
_GOLD = "C9A227"
_FONT = "Calibri"
FMT_EUR = '#,##0;(#,##0);"-"'
FMT_PCT = "0.0%;(0.0%);\"-\""

_titre = Font(name=_FONT, size=14, bold=True, color="FFFFFF")
_entete = Font(name=_FONT, size=10, bold=True, color="FFFFFF")
_gras = Font(name=_FONT, size=10, bold=True)
_normal = Font(name=_FONT, size=10)
_fill_navy = PatternFill("solid", fgColor=_NAVY)
_fill_gold = PatternFill("solid", fgColor=_GOLD)
_fill_gris = PatternFill("solid", fgColor="F2F4F8")
_centre = Alignment(horizontal="center", vertical="center")
_gauche = Alignment(horizontal="left", vertical="center", wrap_text=True)
_bord = Border(*[Side(style="thin", color="D0D5DD")] * 4)


def _entete_dossier(ws, client: str, cloture: str, titre: str) -> None:
    """Écrit le bloc d'en-tête commun (calqué sur les feuilles Datayoyo)."""
    ws["B2"] = client; ws["B2"].font = _gras
    ws["G2"] = "Exercice :"; ws["G2"].font = _normal
    ws["H2"] = cloture; ws["H2"].font = _gras
    ws.merge_cells("B4:F4")
    ws["B4"] = titre; ws["B4"].font = Font(name=_FONT, size=12, bold=True, color=_NAVY)
    ws["B6"] = "Collaborateur :"; ws["E6"] = "Date :"
    ws["B7"] = "Responsable :"; ws["E7"] = "Date de revue :"
    for c in ("B6", "B7", "E6", "E7"):
        ws[c].font = _normal


def _feuille_maitresse(wb: Workbook, code_cycle: str, lignes: list[LigneBalance],
                       client: str, cloture: str) -> None:
    ws = wb.create_sheet(f"FM - {libelle_cycle(code_cycle).upper()[:25]}")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, f"{libelle_cycle(code_cycle).upper()} — Feuille maîtresse")

    # En-têtes du tableau (ligne 9)
    cols = ["Compte(s) comptable(s)", "Solde N", "Solde N-1", "Variation", "%", "Référence de la procédure"]
    for i, titre in enumerate(cols):
        cell = ws.cell(row=9, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord

    r = 10
    for lb in sorted(lignes, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        c_n = ws.cell(row=r, column=3, value=round(lb.solde_n, 2)); c_n.number_format = FMT_EUR
        c_n1 = ws.cell(row=r, column=4, value=round(lb.solde_n1, 2)); c_n1.number_format = FMT_EUR
        # Variation = Solde N - Solde N-1 (formule)
        col_n, col_n1 = get_column_letter(3), get_column_letter(4)
        c_var = ws.cell(row=r, column=5, value=f"={col_n}{r}-{col_n1}{r}"); c_var.number_format = FMT_EUR
        # % = Variation / |Solde N-1|, protégé contre division par zéro
        c_pct = ws.cell(row=r, column=6,
                        value=f'=IF({col_n1}{r}=0,"-",{get_column_letter(5)}{r}/ABS({col_n1}{r}))')
        c_pct.number_format = FMT_PCT
        for col in range(2, 8):
            ws.cell(row=r, column=col).border = _bord
        r += 1

    # Total
    if r > 10:
        ws.cell(row=r, column=2, value="TOTAL").font = _gras
        for col, lettre in ((3, "C"), (4, "D"), (5, "E")):
            t = ws.cell(row=r, column=col, value=f"=SUM({lettre}10:{lettre}{r-1})")
            t.number_format = FMT_EUR; t.font = _gras; t.fill = _fill_gris
        ws.cell(row=r, column=2).fill = _fill_gris

    widths = {"A": 3, "B": 46, "C": 16, "D": 16, "E": 16, "F": 10, "G": 30}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _feuille_travail(wb: Workbook, code_cycle: str, client: str, cloture: str) -> None:
    lib = libelle_cycle(code_cycle)
    ws = wb.create_sheet(f"Travail - {lib[:21]}")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, f"{lib} — Programme de travail")
    ws["B9"] = "OBJECTIFS :"; ws["B9"].font = _gras
    ws.merge_cells("B10:H11"); ws["B10"] = OBJECTIF_GENERIQUE; ws["B10"].alignment = _gauche
    ws["B13"] = "TRAVAUX À EFFECTUER :"; ws["B13"].font = _gras
    r = 14
    for t in travaux(code_cycle):
        ws.merge_cells(f"B{r}:H{r}")
        ws[f"B{r}"] = f"- {t}"; ws[f"B{r}"].alignment = _gauche; ws[f"B{r}"].font = _normal
        r += 1
    for col, w in {"A": 3, "B": 22, "C": 14, "D": 14, "E": 14, "F": 14, "G": 14, "H": 14}.items():
        ws.column_dimensions[col].width = w


# Libellés du tableau de variation par cycle (ouverture / augmentation / diminution / clôture)
# Libellés du tableau de variation par cycle (calqués sur les gabarits Datayoyo).
VARIATION_LABELS: dict[str, tuple[str, str, str, str]] = {
    "IMMO_CORP": ("Valeur brute N-1", "Acquisitions", "Cessions / sorties", "Valeur brute N"),
    "IMMO_FI": ("Valeur brute N-1", "Acquisitions", "Cessions / sorties", "Valeur brute N"),
    "STOCKS": ("Valeur brute N-1", "Entrées", "Sorties", "Valeur brute N"),
    "FONDS_PROPRES": ("Solde N-1", "Augmentations", "Diminutions", "Solde N"),
    "PRC": ("Provision N-1", "Dotations", "Reprises", "Provision N"),
    "AFFILIES": ("Solde N-1", "Augmentations", "Diminutions", "Solde N"),
}


def _feuille_variation_emprunts(wb: Workbook, lignes: list[LigneBalance], client: str, cloture: str) -> None:
    """Tableau de variation des emprunts (gabarit Datataoyo '8_Emprunts')."""
    ws = wb.create_sheet("Variation emprunts")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, "Emprunts — Tableau de variation et revue")
    ws["B9"] = "1. Tableau de variation des emprunts"; ws["B9"].font = _gras
    cols = ["Emprunt", "Montant initial", "Restant dû N-1", "Mvt débit", "Mvt crédit",
            "Restant dû N", "Mvts conformes ?", "Circularisation OK ?", "< 1 an", "1 à 5 ans", "> 5 ans"]
    for i, titre in enumerate(cols):
        cell = ws.cell(row=11, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord
    r = 12
    for lb in sorted(lignes, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        # Montant initial (à saisir), restant dû N-1 = solde_n1, mvts, restant dû N = solde_n
        ws.cell(row=r, column=4, value=round(lb.solde_n1, 2)).number_format = FMT_EUR
        ws.cell(row=r, column=5, value=round(lb.mvt_debit_n, 2)).number_format = FMT_EUR
        ws.cell(row=r, column=6, value=round(lb.mvt_credit_n, 2)).number_format = FMT_EUR
        ws.cell(row=r, column=7, value=round(lb.solde_n, 2)).number_format = FMT_EUR
        for col in range(2, 13):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    if r > 12:
        ws.cell(row=r, column=2, value="TOTAL").font = _gras
        for col, lettre in ((4, "D"), (5, "E"), (6, "F"), (7, "G")):
            t = ws.cell(row=r, column=col, value=f"=SUM({lettre}12:{lettre}{r-1})")
            t.number_format = FMT_EUR; t.font = _gras; t.fill = _fill_gris
    widths = {"A": 3, "B": 40, "C": 14, "D": 15, "E": 13, "F": 13, "G": 15, "H": 15, "I": 15, "J": 11, "K": 11, "L": 11}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def _feuille_balance_agee(wb: Workbook, lignes: list[LigneBalance], cycle_lib: str,
                          client: str, cloture: str) -> None:
    """Balance âgée + cadrage (gabarit Datayoyo Fournisseurs/Clients)."""
    ws = wb.create_sheet("Balance âgée")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, f"{cycle_lib} — Balance âgée")
    total = round(sum(l.solde_n for l in lignes), 2)
    # Cadrage préliminaire
    ws["B9"] = "Cadrage préliminaire"; ws["B9"].font = _gras
    ws["B10"] = "Solde des comptes de tiers"; ws["D10"] = total; ws["D10"].number_format = FMT_EUR
    ws["B11"] = "Solde des écritures non lettrées"; ws["D11"] = 0; ws["D11"].number_format = FMT_EUR
    ws["B12"] = "Écart"; ws["D12"] = "=D10-D11"; ws["D12"].number_format = FMT_EUR
    for c in ("B10", "B11", "B12"):
        ws[c].font = _normal
    # Grille âgée
    cols = ["Tiers", "Solde total", "Non échu", "0-30 j", "30-60 j", "60-90 j", "> 90 j"]
    for i, titre in enumerate(cols):
        cell = ws.cell(row=14, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord
    r = 15
    for lb in sorted(lignes, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        ws.cell(row=r, column=3, value=round(lb.solde_n, 2)).number_format = FMT_EUR
        for col in range(2, 9):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    for col, w in {"A": 3, "B": 40, "C": 15, "D": 13, "E": 12, "F": 12, "G": 12, "H": 12}.items():
        ws.column_dimensions[col].width = w


def _feuille_tableau_variation(wb: Workbook, code_cycle: str, lignes: list[LigneBalance],
                               client: str, cloture: str) -> None:
    """Tableau de variation générique (ouverture → mouvements → clôture + contrôle).

    Les libellés de colonnes s'adaptent au cycle (VARIATION_LABELS). Alimenté par la
    balance : ouverture = Solde N-1, augmentations = Mvt débit, diminutions = Mvt crédit,
    clôture = Solde N. La colonne 'Écart' contrôle : clôture - (ouv. + aug. - dim.)."""
    lib_ouv, lib_aug, lib_dim, lib_clo = VARIATION_LABELS.get(
        code_cycle, ("Solde N-1", "Augmentations", "Diminutions", "Solde N"))
    lib = libelle_cycle(code_cycle)
    ws = wb.create_sheet("Tableau de variation")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, f"{lib} — Tableau de variation")

    cols = ["Compte / poste", lib_ouv, lib_aug, lib_dim, lib_clo, "Écart de contrôle"]
    for i, titre in enumerate(cols):
        cell = ws.cell(row=9, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord

    r = 10
    for lb in sorted(lignes, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        ws.cell(row=r, column=3, value=round(lb.solde_n1, 2)).number_format = FMT_EUR   # ouverture
        ws.cell(row=r, column=4, value=round(lb.mvt_debit_n, 2)).number_format = FMT_EUR   # augmentations
        ws.cell(row=r, column=5, value=round(lb.mvt_credit_n, 2)).number_format = FMT_EUR  # diminutions
        ws.cell(row=r, column=6, value=round(lb.solde_n, 2)).number_format = FMT_EUR      # clôture
        # Écart = clôture - (ouverture + augmentations - diminutions), par formule
        ws.cell(row=r, column=7, value=f"=F{r}-(C{r}+D{r}-E{r})").number_format = FMT_EUR
        for col in range(2, 8):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    if r > 10:
        ws.cell(row=r, column=2, value="TOTAL").font = _gras
        for col, lettre in ((3, "C"), (4, "D"), (5, "E"), (6, "F")):
            t = ws.cell(row=r, column=col, value=f"=SUM({lettre}10:{lettre}{r-1})")
            t.number_format = FMT_EUR; t.font = _gras; t.fill = _fill_gris
        ws.cell(row=r, column=2).fill = _fill_gris
    for col, w in {"A": 3, "B": 42, "C": 15, "D": 15, "E": 15, "F": 15, "G": 16}.items():
        ws.column_dimensions[col].width = w


def _feuille_rappro_bancaire(wb: Workbook, lignes: list[LigneBalance], client: str, cloture: str) -> None:
    """Rapprochement bancaire (gabarit Datayoyo 'Rappro. bancaire')."""
    ws = wb.create_sheet("Rappro. bancaire")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, "Trésorerie — Soldes bancaires et rapprochements")
    cols = ["Libellé banque", "Solde comptable", "Solde relevé", "Écart", "ERB validé ?",
            "Sommes en rapprochement", "Apurées post-clôture", "Non apurées"]
    for i, titre in enumerate(cols):
        c = ws.cell(row=9, column=2 + i, value=titre)
        c.font = _entete; c.fill = _fill_navy; c.alignment = _centre; c.border = _bord
    # comptes de banque (51x) et caisse (53x) du cycle
    banques = [l for l in lignes if l.compte.startswith(("51", "53"))] or lignes
    r = 10
    for lb in sorted(banques, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        ws.cell(row=r, column=3, value=round(lb.solde_n, 2)).number_format = FMT_EUR   # solde comptable
        ws.cell(row=r, column=4, value=0).number_format = FMT_EUR                       # solde relevé (à saisir)
        ws.cell(row=r, column=5, value=f"=C{r}-D{r}").number_format = FMT_EUR           # écart
        for col in range(2, 10):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    if r > 10:
        ws.cell(row=r, column=2, value="TOTAL").font = _gras
        for col, lettre in ((3, "C"), (4, "D"), (5, "E")):
            t = ws.cell(row=r, column=col, value=f"=SUM({lettre}10:{lettre}{r-1})")
            t.number_format = FMT_EUR; t.font = _gras; t.fill = _fill_gris
        ws.cell(row=r, column=2).fill = _fill_gris
    for col, w in {"A": 3, "B": 40, "C": 16, "D": 16, "E": 14, "F": 14, "G": 18, "H": 18, "I": 14}.items():
        ws.column_dimensions[col].width = w


def _feuille_cadrage_dsn(wb: Workbook, lignes: list[LigneBalance], client: str, cloture: str) -> None:
    """Cadrage des salaires FEC (#641/#645) avec la DSN (gabarit '11_Personnel')."""
    ws = wb.create_sheet("Cadrage DSN")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, "Personnel — Cadrage FEC / DSN")
    cols = ["Rubrique (compte)", "Montant FEC", "Montant DSN", "Écart", "Commentaires"]
    for i, titre in enumerate(cols):
        c = ws.cell(row=9, column=2 + i, value=titre)
        c.font = _entete; c.fill = _fill_navy; c.alignment = _centre; c.border = _bord
    paie = [l for l in lignes if l.compte.startswith(("641", "645", "64"))] or lignes
    r = 10
    for lb in sorted(paie, key=lambda x: x.compte):
        ws.cell(row=r, column=2, value=f"{lb.compte} - {lb.libelle}".strip(" -")).font = _normal
        ws.cell(row=r, column=3, value=round(lb.solde_n, 2)).number_format = FMT_EUR   # FEC
        ws.cell(row=r, column=4, value=0).number_format = FMT_EUR                       # DSN (à saisir)
        ws.cell(row=r, column=5, value=f"=C{r}-D{r}").number_format = FMT_EUR           # écart
        for col in range(2, 7):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    for col, w in {"A": 3, "B": 42, "C": 16, "D": 16, "E": 14, "F": 40}.items():
        ws.column_dimensions[col].width = w


def _feuille_analyse_tva(wb: Workbook, lignes: list[LigneBalance], client: str, cloture: str) -> None:
    """Cadrage de la TVA collectée : TVA théorique (base × taux) vs comptabilisée."""
    ws = wb.create_sheet("Analyse TVA")
    ws.sheet_view.showGridLines = False
    _entete_dossier(ws, client, cloture, "Impôts et taxes — Cadrage TVA collectée")
    cols = ["Rubrique", "Base HT (ventes)", "Taux", "TVA théorique", "TVA comptabilisée", "Écart"]
    for i, titre in enumerate(cols):
        c = ws.cell(row=9, column=2 + i, value=titre)
        c.font = _entete; c.fill = _fill_navy; c.alignment = _centre; c.border = _bord
    ws.cell(row=10, column=2, value="TVA au taux normal").font = _normal
    ws.cell(row=10, column=4, value=0.20); ws.cell(row=10, column=4).number_format = "0%"  # taux (saisi)
    ws.cell(row=10, column=5, value="=C10*D10").number_format = FMT_EUR   # TVA théorique = base × taux
    # TVA comptabilisée : comptes 4457 (TVA collectée)
    tva_compta = round(sum(abs(l.solde_n) for l in lignes if l.compte.startswith("4457")), 2)
    ws.cell(row=10, column=6, value=tva_compta).number_format = FMT_EUR
    ws.cell(row=10, column=7, value="=E10-F10").number_format = FMT_EUR   # écart
    for col in range(2, 8):
        ws.cell(row=10, column=col).border = _bord
    for col, w in {"A": 3, "B": 26, "C": 16, "D": 8, "E": 16, "F": 18, "G": 14}.items():
        ws.column_dimensions[col].width = w


def generer_cycle_xlsx(db: Session, mission_id: int, code_cycle: str,
                       edite_par: str | None = None) -> bytes:
    """Génère le classeur (Feuille Maîtresse + Programme de travail) d'un cycle."""
    mission = db.get(Mission, mission_id)
    if not mission:
        raise ValueError("Mission introuvable")
    client = mission.client.raison_sociale if mission.client else ""
    cloture = str(mission.date_cloture) if mission.date_cloture else mission.exercice

    lignes = [
        lb for lb in db.query(LigneBalance).filter_by(mission_id=mission_id).all()
        if cycle_pour_cs(lb.cs_standard) == code_cycle
    ]

    wb = Workbook()
    wb.remove(wb.active)  # retirer la feuille vide par défaut
    _feuille_maitresse(wb, code_cycle, lignes, client, cloture)
    # Feuilles de travail spécifiques selon le cycle
    if code_cycle == "EMPRUNTS":
        _feuille_variation_emprunts(wb, lignes, client, cloture)
    elif code_cycle in ("FOURNISSEURS", "CLIENTS"):
        _feuille_balance_agee(wb, lignes, libelle_cycle(code_cycle), client, cloture)
    elif code_cycle in ("IMMO_CORP", "IMMO_FI", "STOCKS", "FONDS_PROPRES", "PRC", "AFFILIES"):
        _feuille_tableau_variation(wb, code_cycle, lignes, client, cloture)
    elif code_cycle == "TRESORERIE":
        _feuille_rappro_bancaire(wb, lignes, client, cloture)
    elif code_cycle == "PERSONNEL":
        _feuille_cadrage_dsn(wb, lignes, client, cloture)
    elif code_cycle == "IMPOTS":
        _feuille_analyse_tva(wb, lignes, client, cloture)
    elif code_cycle in VARIATION_LABELS:
        _feuille_tableau_variation(wb, code_cycle, lignes, client, cloture)
    _feuille_travail(wb, code_cycle, client, cloture)

    if edite_par and wb.worksheets:
        ws = wb.worksheets[0]
        cachet = ws.cell(row=ws.max_row + 2, column=2,
                         value=f"Édité le {date.today():%d/%m/%Y} par {edite_par}.")
        cachet.font = Font(name=_FONT, size=9, italic=True, color="667085")

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _feuille_synthese(wb: Workbook, mission: Mission, client: str, cloture: str,
                      groupes: dict[str, list[LigneBalance]], seuils: Threshold | None,
                      attention: dict, edite_par: str | None = None) -> None:
    """Feuille de garde : identité, seuils, points d'attention, récap par cycle."""
    ws = wb.create_sheet("Synthèse")
    ws.sheet_view.showGridLines = False

    # Bandeau titre
    ws.merge_cells("B2:G2")
    t = ws.cell(row=2, column=2, value="DOSSIER DE TRAVAIL — SYNTHÈSE")
    t.font = Font(name=_FONT, size=14, bold=True, color="FFFFFF")
    t.alignment = _centre
    for c in range(2, 8):
        ws.cell(row=2, column=c).fill = _fill_navy

    # Bloc identité mission
    infos = [
        ("Client", client or "—"),
        ("Exercice / clôture", cloture or "—"),
        ("Référentiel", mission.referentiel or "—"),
        ("Devise", mission.devise or "—"),
    ]
    r = 4
    for libelle, valeur in infos:
        ws.cell(row=r, column=2, value=libelle).font = _gras
        ws.cell(row=r, column=3, value=valeur).font = _normal
        r += 1

    # Bloc seuils
    r += 1
    ws.cell(row=r, column=2, value="SEUILS RETENUS").font = _entete
    ws.cell(row=r, column=2).fill = _fill_navy
    ws.cell(row=r, column=2).alignment = Alignment(horizontal="left", vertical="center")
    for c in range(3, 8):
        ws.cell(row=r, column=c).fill = _fill_navy
    r += 1
    if seuils and seuils.seuil_signification:
        for libelle, valeur in (
            ("Seuil de signification", seuils.seuil_signification),
            ("Seuil de planification", seuils.seuil_planification),
            ("Seuil de remontée", seuils.seuil_remontee),
        ):
            ws.cell(row=r, column=2, value=libelle).font = _normal
            v = ws.cell(row=r, column=3, value=round(valeur or 0.0, 2)); v.number_format = FMT_EUR
            r += 1
        ws.cell(row=r, column=2, value="Base retenue").font = _normal
        ws.cell(row=r, column=3, value=seuils.base_retenue or "—").font = _normal
        r += 1
    else:
        ws.cell(row=r, column=2,
                value="Seuils non renseignés — à saisir dans l'écran « Seuils » de la mission.").font = _normal
        r += 1

    # Bloc points d'attention (synthèse des signaux de fin de mission)
    r += 1
    ws.cell(row=r, column=2, value="POINTS D'ATTENTION").font = _entete
    for c in range(2, 9):
        ws.cell(row=r, column=c).fill = _fill_navy
    ws.cell(row=r, column=2).alignment = Alignment(horizontal="left", vertical="center")
    r += 1
    resume = (f"Cycles en anomalie : {attention['cycles_anomalie']}  ·  "
              f"Risques élevés/critiques : {attention['risques_eleves']}  ·  "
              f"Contrôles internes déficients : {attention['ci_deficients']}  ·  "
              f"Contrôles automatiques en échec : {attention.get('controles_anomalies', 0)}  ·  "
              f"Variations significatives (> seuil) : {attention.get('nb_variations', 0)}")
    ws.cell(row=r, column=2, value=resume).font = _gras
    r += 1
    benford = attention.get("benford") or {}
    if benford.get("exploitable"):
        ws.cell(row=r, column=2, value=(
            f"Loi de Benford (soldes N) : {benford['conformite']} "
            f"(MAD {benford['mad']}, n={benford['n']}) — indicateur analytique, non probant.")).font = _normal
        r += 1
    ff = attention.get("fraude_fec")
    if ff is not None:
        wd = f"{ff.window_part * 100:.1f}%" if ff.window_applicable else "n/a"
        ws.cell(row=r, column=2, value=(
            f"Analyse fraude FEC (NEP 240) : structuration {ff.structuration_nb} · "
            f"window dressing {wd}{' (suspicion)' if ff.window_suspicion else ''} · "
            f"nombres ronds {ff.nombres_ronds_nb} · doublons {ff.doublons_nb} · "
            f"contrepassations {ff.contrepassations_nb} — signaux non probants.")).font = _normal
        r += 1
        if ff.tva_applicable:
            ws.cell(row=r, column=2, value=(
                f"Cohérence TVA : taux collecté implicite {ff.tva_taux_implicite * 100:.1f}%"
                f"{' — à justifier' if not ff.tva_plausible else ' (dans la bande plausible)'}.")).font = _normal
            r += 1
        if ff.tiers_fournisseurs_nb:
            ws.cell(row=r, column=2, value=(
                f"Tiers fournisseurs : {ff.tiers_fournisseurs_nb} auxiliaires · "
                f"concentration 1er {ff.tiers_top_part * 100:.1f}% · "
                f"montants exclusivement ronds {ff.tiers_ronds_nb} · "
                f"écriture unique élevée {ff.tiers_uniques_eleves_nb} — signaux non probants.")).font = _normal
            r += 1
        from app.services.fraude_fec_service import signaux_orm
        nb_sig, libelles = signaux_orm(ff)
        ws.cell(row=r, column=2, value=(
            f"Vigilance fraude (NEP 240) : {nb_sig} signal(aux) déclenché(s)"
            f"{' — ' + ', '.join(libelles) if libelles else ''}. "
            "Indicateur agrégé, requiert le jugement de l'auditeur.")).font = _gras
        r += 1

    # Récap par cycle (avec anomalie et conclusion saisie)
    r += 1
    entetes = ["Cycle", "Nb comptes", "Total Solde N", "Total Solde N-1", "Variation",
               "Anomalie", "Conclusion"]
    for i, titre in enumerate(entetes):
        cell = ws.cell(row=r, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord
    r += 1
    premiere = r
    conclusions = attention["conclusions"]
    for code in CYCLES:
        lignes = groupes.get(code)
        if not lignes:
            continue
        tot_n = sum(lb.solde_n for lb in lignes)
        tot_n1 = sum(lb.solde_n1 for lb in lignes)
        cc = conclusions.get(code)
        ws.cell(row=r, column=2, value=libelle_cycle(code)).font = _normal
        ws.cell(row=r, column=3, value=len(lignes)).alignment = _centre
        cn = ws.cell(row=r, column=4, value=round(tot_n, 2)); cn.number_format = FMT_EUR
        cn1 = ws.cell(row=r, column=5, value=round(tot_n1, 2)); cn1.number_format = FMT_EUR
        ws.cell(row=r, column=6, value=f"=D{r}-E{r}").number_format = FMT_EUR
        anom = ws.cell(row=r, column=7, value="Oui" if (cc and cc.anomalie) else "—")
        anom.alignment = _centre
        if cc and cc.anomalie:
            anom.font = Font(name=_FONT, size=10, bold=True, color="B42318")
        texte = (cc.conclusion if cc else "").strip()
        ws.cell(row=r, column=8, value=(texte[:80] + "…") if len(texte) > 80 else texte).font = _normal
        for c in range(2, 9):
            ws.cell(row=r, column=c).border = _bord
        r += 1
    if r > premiere:
        ws.cell(row=r, column=2, value="TOTAL").font = _gras
        for col, lettre in ((4, "D"), (5, "E"), (6, "F")):
            tc = ws.cell(row=r, column=col, value=f"=SUM({lettre}{premiere}:{lettre}{r-1})")
            tc.number_format = FMT_EUR; tc.font = _gras; tc.fill = _fill_gris
        for c in (2, 3):
            ws.cell(row=r, column=c).fill = _fill_gris
    else:
        ws.cell(row=r, column=2, value="Aucune ligne de balance importée.").font = _normal

    for col, w in {"A": 3, "B": 40, "C": 12, "D": 15, "E": 15, "F": 15,
                   "G": 11, "H": 46}.items():
        ws.column_dimensions[col].width = w

    if edite_par:
        cachet = ws.cell(row=r + 2, column=2, value=f"Édité le {date.today():%d/%m/%Y} par {edite_par}.")
        cachet.font = Font(name=_FONT, size=9, italic=True, color="667085")


def _feuille_controles(wb: Workbook, controles: list[dict]) -> None:
    """Feuille des contrôles automatiques déterministes sur la balance."""
    ws = wb.create_sheet("Contrôles")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("B2:D2")
    t = ws.cell(row=2, column=2, value="CONTRÔLES AUTOMATIQUES")
    t.font = Font(name=_FONT, size=13, bold=True, color="FFFFFF"); t.alignment = _centre
    for c in range(2, 5):
        ws.cell(row=2, column=c).fill = _fill_navy

    entetes = ["Contrôle", "Statut", "Détail"]
    for i, titre in enumerate(entetes):
        cell = ws.cell(row=4, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord
    r = 5
    for c in controles:
        ws.cell(row=r, column=2, value=c["libelle"]).font = _normal
        st = ws.cell(row=r, column=3, value="OK" if c["statut"] == "ok" else "ANOMALIE")
        st.alignment = _centre
        st.font = (Font(name=_FONT, size=10, bold=True, color="067647") if c["statut"] == "ok"
                   else Font(name=_FONT, size=10, bold=True, color="B42318"))
        ws.cell(row=r, column=4, value=c["detail"]).font = _normal
        for col in range(2, 5):
            ws.cell(row=r, column=col).border = _bord
        r += 1
    for col, w in {"A": 3, "B": 32, "C": 13, "D": 60}.items():
        ws.column_dimensions[col].width = w


def _feuille_variations(wb: Workbook, variations: list[dict], seuil: float, devise: str) -> None:
    """Feuille des variations N/N-1 dépassant le seuil de signification (NEP 520)."""
    ws = wb.create_sheet("Variations significatives")
    ws.sheet_view.showGridLines = False
    ws.merge_cells("B2:F2")
    t = ws.cell(row=2, column=2, value="VARIATIONS SIGNIFICATIVES (> SEUIL)")
    t.font = Font(name=_FONT, size=13, bold=True, color="FFFFFF"); t.alignment = _centre
    for c in range(2, 7):
        ws.cell(row=2, column=c).fill = _fill_navy
    ws.cell(row=3, column=2,
            value=f"Seuil de signification appliqué : {round(seuil, 2)} {devise}").font = _normal

    entetes = ["Compte", "Solde N", "Solde N-1", "Variation", "Variation %"]
    for i, titre in enumerate(entetes):
        cell = ws.cell(row=5, column=2 + i, value=titre)
        cell.font = _entete; cell.fill = _fill_navy; cell.alignment = _centre; cell.border = _bord
    r = 6
    for v in sorted(variations, key=lambda x: abs(x["variation"]), reverse=True):
        ws.cell(row=r, column=2, value=f"{v['compte']} - {v['libelle']}".strip(" -")).font = _normal
        ws.cell(row=r, column=3, value=v["solde_n"]).number_format = FMT_EUR
        ws.cell(row=r, column=4, value=v["solde_n1"]).number_format = FMT_EUR
        ws.cell(row=r, column=5, value=v["variation"]).number_format = FMT_EUR
        pct = ws.cell(row=r, column=6, value=(v["variation_pct"] if v["variation_pct"] is not None else ""))
        pct.number_format = "0.0%"
        for c in range(2, 7):
            ws.cell(row=r, column=c).border = _bord
        r += 1
    if r == 6:
        ws.cell(row=r, column=2,
                value="Aucune variation supérieure au seuil (ou seuil non renseigné).").font = _normal
    for col, w in {"A": 3, "B": 42, "C": 16, "D": 16, "E": 16, "F": 13}.items():
        ws.column_dimensions[col].width = w


def generer_dossier_xlsx(db: Session, mission_id: int, edite_par: str | None = None) -> bytes:
    """Classeur unique : Synthèse + Contrôles + Variations significatives + une FM par cycle présent."""
    data = synthese_service.collecter(db, mission_id)
    groupes = data["groupes"]
    attention = {
        "conclusions": data["conclusions"],
        "cycles_anomalie": data["cycles_anomalie"],
        "risques_eleves": data["risques_eleves"],
        "ci_deficients": data["ci_deficients"],
        "benford": data["benford"],
        "controles_anomalies": data["controles_anomalies"],
        "nb_variations": data["nb_variations_significatives"],
        "fraude_fec": data.get("fraude_fec"),
    }

    wb = Workbook()
    wb.remove(wb.active)
    _feuille_synthese(wb, data["mission"], data["client"], data["cloture"],
                      groupes, data["seuils"], attention, edite_par)
    _feuille_controles(wb, data["controles"])
    _feuille_variations(wb, data["variations_significatives"], data["seuil_signif"],
                        data["mission"].devise or "")
    for code in CYCLES:  # ordre stable, une FM par cycle présent
        if groupes.get(code):
            _feuille_maitresse(wb, code, groupes[code], data["client"], data["cloture"])

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
