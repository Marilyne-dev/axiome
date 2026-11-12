"""Module 17 — feuille de garde (synthèse du dossier) en DOCX."""
from __future__ import annotations

import io

import docx

from app.models.audit import Threshold
from app.models.balance import LigneBalance
from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.conclusion import CycleConclusion
from app.models.mission import Mission
from app.services.rapports_service import feuille_garde
from app.services.synthese_service import collecter


def _mission(db):
    cab = Cabinet(nom="C"); db.add(cab); db.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Gamma SA"); db.add(cl); db.flush()
    m = Mission(client_id=cl.id, intitule="Audit 2025", referentiel="PCG_FR",
                pays="France", devise="EUR", exercice="2025")
    db.add(m); db.flush()
    for i in range(3):
        db.add(LigneBalance(mission_id=m.id, compte=f"{512000 + i}", libelle=f"Banque {i}",
                            cs_standard="TRESORERIE", solde_n=1000 + i * 100, solde_n1=900))
    db.add(Threshold(mission_id=m.id, seuil_signification=1500, seuil_planification=1100,
                     seuil_remontee=75, base_retenue="resultat_net"))
    db.add(CycleConclusion(mission_id=m.id, cycle_code="TRESORERIE",
                           conclusion="Rapprochement validé, écart nul.", anomalie=True))
    db.commit()
    return m


def _texte(contenu: bytes) -> str:
    d = docx.Document(io.BytesIO(contenu))
    lignes = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            lignes.extend(c.text for c in row.cells)
    return "\n".join(lignes)


def test_feuille_garde_contenu(db_session):
    m = _mission(db_session)
    contenu = feuille_garde(m, collecter(db_session, m.id))
    assert contenu[:2] == b"PK"  # DOCX = archive zip
    txt = _texte(contenu)
    assert "Feuille de garde" in txt
    assert "Seuils retenus" in txt and "Signification" in txt
    assert "Points d'attention" in txt
    assert "Trésorerie" in txt          # récap par cycle
    assert "Oui" in txt                  # anomalie signalée


def test_feuille_garde_sans_seuils(db_session):
    cab = Cabinet(nom="C"); db_session.add(cab); db_session.flush()
    cl = Client(cabinet_id=cab.id, raison_sociale="Vide"); db_session.add(cl); db_session.flush()
    m = Mission(client_id=cl.id, intitule="M", referentiel="PCG_FR", pays="France", devise="EUR")
    db_session.add(m); db_session.commit()
    txt = _texte(feuille_garde(m, collecter(db_session, m.id)))
    assert "non renseignés" in txt
    assert "Aucune ligne de balance importée." in txt


def test_feuille_garde_cachet_edition(db_session):
    m = _mission(db_session)
    data = collecter(db_session, m.id)
    # Avec auteur : cachet présent ; sans : absent.
    avec = _texte(feuille_garde(m, data, edite_par="Camille Associé"))
    sans = _texte(feuille_garde(m, data))
    assert "Édité le" in avec and "Camille Associé" in avec
    assert "Édité le" not in sans
