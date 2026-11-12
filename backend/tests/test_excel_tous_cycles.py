"""Module 20 — génération sans erreur pour les 13 cycles + tableau de variation."""
from __future__ import annotations

import io
import warnings

import openpyxl

from app.core.cycles_ref import CYCLES
from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services.excel_service import generer_cycle_xlsx


def _mission(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Omega"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.flush()
    db.add(LigneBalance(mission_id=m.id, compte="200000", libelle="Poste", cs_standard="",
                        solde_n=100, solde_n1=80, mvt_debit_n=30, mvt_credit_n=10))
    db.commit()
    return m.id


def test_generation_tous_cycles_sans_erreur(db_session):
    mid = _mission(db_session)
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # un nom d'onglet > 31 car. échouerait
        for code in CYCLES:
            wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, code)))
            assert any(s.startswith("FM") for s in wb.sheetnames)
            assert all(len(s) <= 31 for s in wb.sheetnames)


def test_tableau_variation_ecart(db_session):
    mid = _mission(db_session)
    # ligne rattachée au cycle STOCKS (sinon filtrée hors du tableau)
    db_session.add(LigneBalance(mission_id=mid, compte="370000", libelle="Stocks", cs_standard="STOCKS",
                                solde_n=100, solde_n1=80, mvt_debit_n=30, mvt_credit_n=10))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "STOCKS")))
    assert "Tableau de variation" in wb.sheetnames
    ws = wb["Tableau de variation"]
    entetes = [ws.cell(row=9, column=c).value for c in range(2, 8)]
    assert entetes[0] == "Compte / poste" and entetes[5] == "Écart de contrôle"
    # colonne écart = formule de contrôle clôture - (ouv + aug - dim)
    assert str(ws.cell(row=10, column=7).value).startswith("=F10-(C10+D10-E10)")


def test_libelles_variation_par_cycle(db_session):
    mid = _mission(db_session)
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "PRC")))
    ws = wb["Tableau de variation"]
    # PRC : libellés provisions
    assert ws.cell(row=9, column=3).value == "Provision N-1"
    assert ws.cell(row=9, column=4).value == "Dotations"


def test_tresorerie_rappro_bancaire(db_session):
    mid = _mission(db_session)
    db_session.add(LigneBalance(mission_id=mid, compte="512000", libelle="Banque", cs_standard="TRESORERIE",
                                solde_n=25000, solde_n1=20000))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "TRESORERIE")))
    assert "Rappro. bancaire" in wb.sheetnames
    ws = wb["Rappro. bancaire"]
    entetes = [ws.cell(row=9, column=c).value for c in range(2, 6)]
    assert entetes == ["Libellé banque", "Solde comptable", "Solde relevé", "Écart"]
    assert str(ws.cell(row=10, column=5).value).startswith("=C10-D10")  # écart en formule


def test_personnel_cadrage_dsn(db_session):
    mid = _mission(db_session)
    db_session.add(LigneBalance(mission_id=mid, compte="641000", libelle="Salaires",
                                cs_standard="PERSONNEL ET COMPTES RATTACHES", solde_n=500000, solde_n1=480000))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "PERSONNEL")))
    assert "Cadrage DSN" in wb.sheetnames
    ws = wb["Cadrage DSN"]
    assert [ws.cell(row=9, column=c).value for c in range(2, 6)] == \
        ["Rubrique (compte)", "Montant FEC", "Montant DSN", "Écart"]


def test_impots_analyse_tva(db_session):
    mid = _mission(db_session)
    db_session.add(LigneBalance(mission_id=mid, compte="445710", libelle="TVA collectée",
                                cs_standard="ETAT ET AUTRES COLLECTIVITES", solde_n=120000, solde_n1=100000))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "IMPOTS")))
    assert "Analyse TVA" in wb.sheetnames
    ws = wb["Analyse TVA"]
    assert ws.cell(row=9, column=5).value == "TVA théorique"
    assert str(ws.cell(row=10, column=5).value).startswith("=C10*D10")  # base × taux
