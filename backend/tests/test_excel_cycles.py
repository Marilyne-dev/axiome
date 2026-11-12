"""Module 20 — feuilles spécifiques : variation emprunts + balance âgée."""
from __future__ import annotations

import io

import openpyxl

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services.excel_service import generer_cycle_xlsx


def _mission(db, comptes, cs):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Lambda"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.flush()
    for cpte, lib, sn, sn1 in comptes:
        db.add(LigneBalance(mission_id=m.id, compte=cpte, libelle=lib, cs_standard=cs, solde_n=sn, solde_n1=sn1))
    db.commit()
    return m.id


def test_emprunts_a_feuille_variation(db_session):
    mid = _mission(db_session, [("164000", "Emprunt banque", 40000, 60000)], "EMPRUNTS ET DETTES ASSIMILEES")
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "EMPRUNTS")))
    assert "Variation emprunts" in wb.sheetnames
    ws = wb["Variation emprunts"]
    entetes = [ws.cell(row=11, column=c).value for c in range(2, 8)]
    assert entetes[0] == "Emprunt" and "Restant dû N" in entetes[5]


def test_fournisseurs_a_balance_agee(db_session):
    mid = _mission(db_session, [("401000", "Frs Alpha", 15000, 12000)], "FOURNISSEURS ET COMPTES RATTACHES")
    wb = openpyxl.load_workbook(io.BytesIO(generer_cycle_xlsx(db_session, mid, "FOURNISSEURS")))
    assert "Balance âgée" in wb.sheetnames
    ws = wb["Balance âgée"]
    entetes = [ws.cell(row=14, column=c).value for c in range(2, 9)]
    assert entetes[0] == "Tiers" and "> 90 j" in entetes
