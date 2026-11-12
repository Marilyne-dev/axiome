"""Contrôles automatiques déterministes sur la balance + onglet Contrôles du dossier."""
from __future__ import annotations

import io

import openpyxl

from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.services import controles_service
from app.services.excel_service import generer_dossier_xlsx


class _L:
    def __init__(self, compte, libelle, solde_n, solde_n1, mvt_debit_n, mvt_credit_n):
        self.compte = compte
        self.libelle = libelle
        self.solde_n = solde_n
        self.solde_n1 = solde_n1
        self.mvt_debit_n = mvt_debit_n
        self.mvt_credit_n = mvt_credit_n


def test_balance_saine_aucune_anomalie():
    lignes = [
        _L("512", "Banque", 1200, 1000, 200, 0),
        _L("164", "Emprunt", -1200, -1000, 0, 200),
    ]
    res = controles_service.controler(lignes)
    assert res["nb_anomalies"] == 0
    assert all(c["statut"] == "ok" for c in res["controles"])


def test_balance_a_problemes_detecte_tout():
    lignes = [
        _L("512", "", 1200, 1000, 300, 0),   # sans libellé, hors bouclage, déséquilibrée
        _L("512", "Banque", 500, 500, 0, 0),  # doublon de compte
    ]
    res = controles_service.controler(lignes)
    libelles = {c["libelle"]: c["statut"] for c in res["controles"]}
    assert libelles["Équilibre des soldes N"] == "anomalie"
    assert libelles["Équilibre des mouvements"] == "anomalie"
    assert libelles["Bouclage ouverture → clôture"] == "anomalie"
    assert libelles["Unicité des comptes"] == "anomalie"
    assert libelles["Libellés renseignés"] == "anomalie"
    assert res["nb_anomalies"] == 5


def test_balance_vide():
    res = controles_service.controler([])
    assert res["nb_anomalies"] == 1


def test_onglet_controles_dans_dossier(db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Delta"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.flush()
    # Balance délibérément hors bouclage.
    db_session.add(LigneBalance(mission_id=m.id, compte="512000", libelle="Banque",
                                cs_standard="TRESORERIE", solde_n=1200, solde_n1=1000,
                                mvt_debit_n=300, mvt_credit_n=0))
    db_session.commit()
    wb = openpyxl.load_workbook(io.BytesIO(generer_dossier_xlsx(db_session, m.id)))
    assert "Contrôles" in wb.sheetnames
    ws = wb["Contrôles"]
    statuts = [ws.cell(row=r, column=3).value for r in range(5, 11) if ws.cell(row=r, column=2).value]
    assert "ANOMALIE" in statuts  # au moins un contrôle en échec
