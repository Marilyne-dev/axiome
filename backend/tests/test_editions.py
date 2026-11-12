"""Journal des éditions — service + intégration web."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.edition import RapportEdition
from app.services import editions_service


def test_enregistrer_et_lister_ordre(db_session):
    editions_service.enregistrer(db_session, 1, "dossier-complet", "XLSX", "Alice")
    editions_service.enregistrer(db_session, 1, "feuille-garde", "pdf", "Bob")
    editions_service.enregistrer(db_session, 2, "lettre-mission", "docx", "Carole")
    lignes = editions_service.lister(db_session, 1)
    assert len(lignes) == 2                       # cloisonné par mission
    assert lignes[0].type_edition == "feuille-garde"  # plus récent d'abord
    assert lignes[0].format == "pdf"               # format normalisé en minuscules


def test_generation_dossier_cree_une_edition(client, db_session):
    mid = mission(db_session)
    r = client.get(f"/missions/{mid}/excel/dossier-complet", cookies=ck(client))
    assert r.status_code == 200
    editions = db_session.query(RapportEdition).filter_by(mission_id=mid).all()
    assert len(editions) == 1
    assert editions[0].type_edition == "dossier-complet" and editions[0].format == "xlsx"
    assert editions[0].par  # auteur renseigné


def test_page_journal_affiche_edition(client, db_session):
    mid = mission(db_session)
    client.get(f"/missions/{mid}/excel/dossier-complet", cookies=ck(client))
    page = client.get(f"/missions/{mid}/vue/editions", cookies=ck(client))
    assert page.status_code == 200
    assert "dossier-complet" in page.text
    assert "Journal des éditions" in page.text


def test_export_csv_journal(client, db_session):
    mid = mission(db_session)
    client.get(f"/missions/{mid}/excel/dossier-complet", cookies=ck(client))
    client.get(f"/missions/{mid}/excel/TRESORERIE", cookies=ck(client))
    r = client.get(f"/missions/{mid}/vue/editions/export.csv", cookies=ck(client))
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    corps = r.text.replace("\ufeff", "")
    lignes = [ligne for ligne in corps.splitlines() if ligne.strip()]
    assert lignes[0].startswith("N°;Date;Heure;Livrable;Format;Généré par")
    assert lignes[1].startswith("1;")                 # n°1 = plus ancienne
    assert "dossier-complet;xlsx" in lignes[1]
    assert "cycle:TRESORERIE;xlsx" in lignes[2]


def test_export_csv_service(db_session):
    editions_service.enregistrer(db_session, 7, "feuille-garde", "pdf", "Alice")
    csv_txt = editions_service.exporter_csv(db_session, 7)
    assert "feuille-garde;pdf;Alice" in csv_txt
