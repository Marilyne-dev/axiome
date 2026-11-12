"""Modules 5 & 20 — import balance + génération Feuille Maîtresse."""
from __future__ import annotations

import io

import openpyxl

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services.excel_service import generer_cycle_xlsx
from app.services.import_service import importer_balance


def _mission(db):
    cab = Cabinet(nom="C", pays="France"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Sigma"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db.add(m); db.commit()
    return m.id


def _balance_xlsx() -> bytes:
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Table_BG"
    ws.append(["KPI[CompteName]", "MappingPCG[CS_STANDARD]", "[v_Gene_Solde_N]", "[v_Gene_Solde_N_1]"])
    ws.append(["51200000 - Banque", "TRESORERIE", 1000, 800])
    ws.append(["16400000 - Emprunts", "EMPRUNTS ET DETTES ASSIMILEES", 5000, 6000])
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()


def test_import_detecte_colonnes(db_session):
    mid = _mission(db_session)
    res = importer_balance(db_session, mid, _balance_xlsx())
    assert res["lignes_importees"] == 2
    assert res["repartition_par_cycle"].get("TRESORERIE") == 1
    lignes = db_session.query(LigneBalance).filter_by(mission_id=mid).all()
    assert {l.compte for l in lignes} == {"51200000", "16400000"}


def test_reimport_idempotent(db_session):
    mid = _mission(db_session)
    importer_balance(db_session, mid, _balance_xlsx())
    importer_balance(db_session, mid, _balance_xlsx())  # réimport
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 2  # pas de doublon


def test_generation_fm_tresorerie(db_session):
    mid = _mission(db_session)
    importer_balance(db_session, mid, _balance_xlsx())
    contenu = generer_cycle_xlsx(db_session, mid, "TRESORERIE")
    wb = openpyxl.load_workbook(io.BytesIO(contenu))
    assert any("FM" in s for s in wb.sheetnames)
    ws = wb[wb.sheetnames[0]]
    entetes = [ws.cell(row=9, column=c).value for c in range(2, 8)]
    assert entetes[:5] == ["Compte(s) comptable(s)", "Solde N", "Solde N-1", "Variation", "%"]
