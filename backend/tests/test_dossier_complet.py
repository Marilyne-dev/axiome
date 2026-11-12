"""Module 20 — classeur de synthèse (dossier complet : Synthèse + Feuilles Maîtresses)."""
from __future__ import annotations

import io

import openpyxl

from app.models.audit import Threshold
from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.conclusion import CycleConclusion
from app.models.mission import Mission
from app.services.excel_service import generer_cycle_xlsx, generer_dossier_xlsx


def _mission_multi(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Lambda"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France",
                devise="EUR", exercice="2025")
    db.add(m); db.flush()
    lignes = [
        ("512000", "Banque", "TRESORERIE", 12000, 10000),
        ("164000", "Emprunt", "EMPRUNTS ET DETTES ASSIMILEES", 40000, 50000),
        ("411000", "Clients", "CLIENTS ET COMPTES RATTACHES", 17000, 15000),
    ]
    for cpte, lib, cs, sn, sn1 in lignes:
        db.add(LigneBalance(mission_id=m.id, compte=cpte, libelle=lib, cs_standard=cs,
                            solde_n=sn, solde_n1=sn1))
    db.add(Threshold(mission_id=m.id, seuil_signification=1200, seuil_planification=900,
                     seuil_remontee=60, base_retenue="resultat_net"))
    db.commit()
    return m.id


def test_dossier_complet_structure(db_session):
    mid = _mission_multi(db_session)
    wb = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, mid)))
    # La feuille Synthèse vient en premier, suivie d'une FM par cycle présent.
    assert wb.sheetnames[0] == "Synthèse"
    assert any(n.startswith("FM - TRÉSORERIE") for n in wb.sheetnames)
    assert any(n.startswith("FM - EMPRUNTS") for n in wb.sheetnames)
    assert any(n.startswith("FM - CLIENTS") for n in wb.sheetnames)
    # Un cycle absent ne génère pas de feuille.
    assert not any("STOCKS" in n for n in wb.sheetnames)


def test_dossier_complet_synthese_contenu(db_session):
    mid = _mission_multi(db_session)
    ws = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, mid)))["Synthèse"]
    cellules = [ws.cell(row=r, column=2).value for r in range(1, 40)]
    assert "DOSSIER DE TRAVAIL — SYNTHÈSE" in cellules
    assert "Seuil de signification" in cellules   # seuils persistés repris
    assert "TOTAL" in cellules                     # ligne de total du récap par cycle


def test_dossier_complet_sans_balance(db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Vide"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, m.id)))
    # Sans balance : Synthèse + Contrôles + Variations significatives (feuilles toujours présentes).
    assert wb.sheetnames == ["Synthèse", "Contrôles", "Variations significatives"]
    cellules = [wb["Synthèse"].cell(row=r, column=2).value for r in range(1, 40)]
    assert any(c and "non renseignés" in c for c in cellules)


def test_dossier_complet_points_attention(db_session):
    mid = _mission_multi(db_session)
    # Marque une anomalie sur le cycle Trésorerie.
    db_session.add(CycleConclusion(mission_id=mid, cycle_code="TRESORERIE",
                                   conclusion="Écart de rapprochement non justifié.", anomalie=True))
    db_session.commit()
    ws = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, mid)))["Synthèse"]
    colB = [ws.cell(row=r, column=2).value for r in range(1, 45)]
    assert "POINTS D'ATTENTION" in colB
    assert any(v and "Cycles en anomalie : 1" in v for v in colB)
    # La ligne Trésorerie porte l'anomalie et l'extrait de conclusion.
    for r in range(1, 45):
        if ws.cell(row=r, column=2).value == "Trésorerie":
            assert ws.cell(row=r, column=7).value == "Oui"
            assert "rapprochement" in (ws.cell(row=r, column=8).value or "")
            break
    else:
        raise AssertionError("Ligne Trésorerie absente du récap")


def test_dossier_complet_signal_benford(db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Benford"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.flush()
    # Assez de montants variés pour rendre l'analyse de Benford exploitable.
    for i in range(40):
        v = 100.0 + i * 137.5
        db_session.add(LigneBalance(mission_id=m.id, compte=f"{500000 + i}", libelle=f"C{i}",
                                    cs_standard="TRESORERIE", solde_n=v, solde_n1=v))
    db_session.commit()
    ws = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, m.id)))["Synthèse"]
    colB = [ws.cell(row=r, column=2).value for r in range(1, 50)]
    assert any(v and "Loi de Benford" in v and "non probant" in v for v in colB)


def test_dossier_variations_significatives(db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Epsilon"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.flush()
    # Une variation > seuil (40000) et une < seuil (100).
    db_session.add(LigneBalance(mission_id=m.id, compte="601000", libelle="Achats",
                                cs_standard="AUTRES COMPTES", solde_n=50000, solde_n1=10000))
    db_session.add(LigneBalance(mission_id=m.id, compte="606000", libelle="Fournitures",
                                cs_standard="AUTRES COMPTES", solde_n=1100, solde_n1=1000))
    db_session.add(Threshold(mission_id=m.id, seuil_signification=5000, seuil_planification=3500,
                             seuil_remontee=250, base_retenue="resultat_net"))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, m.id)))
    assert "Variations significatives" in wb.sheetnames
    ws = wb["Variations significatives"]
    comptes = [ws.cell(row=r, column=2).value for r in range(6, 12) if ws.cell(row=r, column=2).value]
    assert any("601000" in c for c in comptes)          # variation > seuil listée
    assert not any("606000" in c for c in comptes)       # variation < seuil exclue


def test_dossier_cachet_edition(db_session):
    mid = _mission_multi(db_session)
    ws = openpyxl.load_workbook(
        io.BytesIO(generer_dossier_xlsx(db_session, mid, edite_par="Camille Associé")))["Synthèse"]
    colB = [ws.cell(row=r, column=2).value for r in range(1, 60)]
    assert any(v and "Édité le" in v and "Camille Associé" in v for v in colB)
    # Sans auteur : pas de cachet.
    ws2 = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, mid)))["Synthèse"]
    colB2 = [ws2.cell(row=r, column=2).value for r in range(1, 60)]
    assert not any(v and "Édité le" in v for v in colB2)


def test_cycle_xlsx_cachet_edition(db_session):
    mid = _mission_multi(db_session)
    avec = openpyxl.load_workbook(
        io.BytesIO(generer_cycle_xlsx(db_session, mid, "TRESORERIE", edite_par="Camille Associé"))).worksheets[0]
    colB = [avec.cell(row=r, column=2).value for r in range(1, avec.max_row + 1)]
    assert any(v and "Édité le" in str(v) and "Camille Associé" in str(v) for v in colB)
    sans = openpyxl.load_workbook(
        io.BytesIO(generer_cycle_xlsx(db_session, mid, "TRESORERIE"))).worksheets[0]
    colB2 = [sans.cell(row=r, column=2).value for r in range(1, sans.max_row + 1)]
    assert not any(v and "Édité le" in str(v) for v in colB2)
