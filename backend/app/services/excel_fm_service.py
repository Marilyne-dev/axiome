"""Module 20 — Export Excel de la Feuille Maîtresse (structure Datayoyo).

Reproduit fidèlement la mise en page de la Feuille Maîtresse Datayoyo :
bloc d'en-tête (client, cycle, date de clôture, collaborateur/responsable),
puis tableau Compte | Solde N | Solde N-1 | Variation | % | Réf. procédure.
Les colonnes calculées (Variation, %) sont des FORMULES (zéro erreur, cohérence).
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.services.feuille_maitresse_service import FeuilleMaitresse

_FONT = "Arial"
_NAVY = "0B2545"
_GOLD = "C9A227"
_FMT_MONTANT = '#,##0.00;(#,##0.00);"-"'
_FMT_PCT = '0.0%;(0.0%);"-"'


def exporter_feuille_maitresse(
    fm: FeuilleMaitresse, *, client: str, exercice_cloture: str,
    chemin_sortie: str | Path,
) -> Path:
    """Génère le classeur Feuille Maîtresse et retourne le chemin du fichier."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"FM - {fm.cycle}"[:31]

    titre = Font(name=_FONT, bold=True, size=13, color=_NAVY)
    entete = Font(name=_FONT, bold=True, size=10, color="FFFFFF")
    normal = Font(name=_FONT, size=10)
    gras = Font(name=_FONT, bold=True, size=10, color=_NAVY)
    fond_entete = PatternFill("solid", fgColor=_NAVY)
    fond_total = PatternFill("solid", fgColor="EAF0FB")
    bord = Side(style="thin", color="D0D6E2")
    contour = Border(left=bord, right=bord, top=bord, bottom=bord)

    # --- Bloc d'en-tête (calé sur le gabarit réel) ---
    ws["B2"] = client
    ws["B2"].font = titre
    ws["G2"] = "Exercice :"
    ws["H2"] = exercice_cloture
    ws["B4"] = f"{fm.cycle} - Feuille maîtresse"
    ws["B4"].font = Font(name=_FONT, bold=True, size=11, color=_GOLD)
    ws["B6"] = "Collaborateur :"; ws["E6"] = "Date :"
    ws["B7"] = "Responsable :"; ws["E7"] = "Date de revue :"
    for c in ("B6", "B7", "E6", "E7", "G2"):
        ws[c].font = Font(name=_FONT, size=9, italic=True)

    # --- En-tête de tableau (ligne 9) ---
    entetes = {
        "B": "Compte(s) comptable(s)", "D": "Solde N", "E": "Solde N-1",
        "F": "Variation", "G": "%", "H": "Référence de la procédure",
    }
    for col, lib in entetes.items():
        cell = ws[f"{col}9"]
        cell.value = lib
        cell.font = entete
        cell.fill = fond_entete
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = contour

    # --- Ligne de total (ligne 10) ---
    r = 10
    ws[f"B{r}"] = fm.cycle
    ws[f"D{r}"] = fm.total_n
    ws[f"E{r}"] = fm.total_n1
    ws[f"F{r}"] = f"=D{r}-E{r}"
    ws[f"G{r}"] = f'=IF(E{r}=0,"",(D{r}-E{r})/ABS(E{r}))'
    for col in ("B", "D", "E", "F", "G", "H"):
        ws[f"{col}{r}"].font = gras
        ws[f"{col}{r}"].fill = fond_total
        ws[f"{col}{r}"].border = contour
    ws[f"D{r}"].number_format = ws[f"E{r}"].number_format = ws[f"F{r}"].number_format = _FMT_MONTANT
    ws[f"G{r}"].number_format = _FMT_PCT

    # --- Lignes de détail (une par compte) ---
    for i, ligne in enumerate(fm.lignes):
        r = 11 + i
        libelle = f"{ligne.compte} - {ligne.libelle}".strip(" -")
        ws[f"B{r}"] = libelle
        ws[f"D{r}"] = ligne.solde_n
        ws[f"E{r}"] = ligne.solde_n1
        ws[f"F{r}"] = f"=D{r}-E{r}"
        ws[f"G{r}"] = f'=IF(E{r}=0,"",(D{r}-E{r})/ABS(E{r}))'
        for col in ("B", "D", "E", "F", "G", "H"):
            ws[f"{col}{r}"].font = normal
            ws[f"{col}{r}"].border = contour
        ws[f"D{r}"].number_format = ws[f"E{r}"].number_format = ws[f"F{r}"].number_format = _FMT_MONTANT
        ws[f"G{r}"].number_format = _FMT_PCT

    # --- Largeurs de colonnes ---
    largeurs = {"A": 3, "B": 42, "C": 3, "D": 16, "E": 16, "F": 16, "G": 10, "H": 28}
    for col, w in largeurs.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B11"  # fige l'en-tête au défilement

    chemin = Path(chemin_sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    wb.save(chemin)
    return chemin
