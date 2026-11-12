"""Détection de fraude sur écritures FEC (NEP 240) : détecteurs + écran."""
from __future__ import annotations

from datetime import date

from _helpers_ecrans import ck, mission

from app.services.fraude_fec_service import analyser_fec

_COLS = ("JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
         "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
         "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet",
         "ValidDate", "Montantdevise", "Idevise")


def _l(jrn, dt, cpte, deb, cred):
    d = {c: "" for c in _COLS}
    d.update(JournalCode=jrn, EcritureDate=dt, CompteNum=cpte, Debit=deb, Credit=cred)
    return "\t".join(d[c] for c in _COLS)


def _fec(lignes):
    return "\n".join(["\t".join(_COLS), *lignes])


def test_detecte_structuration():
    fec = _fec([_l("BQ", "20250115", "512000", "9500,00", "0"),
                _l("BQ", "20250210", "512000", "9800,00", "0"),
                _l("BQ", "20250310", "512000", "3000,00", "0")])  # sous la bande
    res = analyser_fec(fec, seuil_structuration=10000.0)
    assert res["structuration"]["nb"] == 2
    assert res["structuration"]["borne_basse"] == 9000.0


def test_detecte_window_dressing():
    fec = _fec([_l("AN", "20250101", "101000", "0", "50000,00"),   # à-nouveau exclu
                _l("VT", "20250601", "707000", "0", "1000,00"),
                _l("VT", "20251228", "707000", "0", "9000,00")])   # 5 j avant clôture
    res = analyser_fec(fec, cloture=date(2025, 12, 31))
    wd = res["window_dressing"]
    assert wd["applicable"] and wd["part"] == 0.9 and wd["suspicion"]


def test_window_dressing_sans_cloture_non_applicable():
    fec = _fec([_l("VT", "20250601", "707000", "0", "1000,00")])
    assert analyser_fec(fec, cloture=None)["window_dressing"]["applicable"] is False


def test_detecte_doublons_et_contrepassation():
    fec = _fec([_l("OD", "20250601", "606000", "2000,00", "0"),
                _l("OD", "20250602", "606000", "2000,00", "0"),
                _l("OD", "20250701", "606000", "0", "2000,00")])   # extourne
    res = analyser_fec(fec)
    assert res["doublons"]["nb"] == 1
    assert res["contrepassations"]["nb"] == 1
    assert res["nombres_ronds"]["nb"] == 3


def test_upload_fec_fraude_web(client, db_session):
    mid = mission(db_session)
    fec = _fec([_l("BQ", "20250115", "512000", "9500,00", "0"),
                _l("BQ", "20250210", "512000", "9800,00", "0")])
    r = client.post(f"/missions/{mid}/vue/fraude/fec",
                    files={"fichier": ("fec.txt", fec, "text/plain")},
                    data={"seuil": "10000"}, cookies=ck(client))
    assert r.status_code == 200
    assert "Structuration" in r.text and "NEP 240" in r.text


def test_fraude_fec_persiste_dans_synthese(client, db_session):
    from app.services import synthese_service
    mid = mission(db_session)
    fec = _fec([_l("BQ", "20250115", "512000", "9500,00", "0"),
                _l("BQ", "20250210", "512000", "9800,00", "0")])
    client.post(f"/missions/{mid}/vue/fraude/fec",
                files={"fichier": ("fec.txt", fec, "text/plain")},
                data={"seuil": "10000"}, cookies=ck(client))
    data = synthese_service.collecter(db_session, mid)
    ff = data["fraude_fec"]
    assert ff is not None and ff.structuration_nb == 2 and ff.n_ecritures == 2


def test_coherence_tva():
    fec = _fec([_l("VT", "20250131", "707000", "0", "10000,00"),
                _l("VT", "20250131", "445710", "0", "2000,00")])
    tva = analyser_fec(fec)["tva"]
    assert tva["applicable"] and tva["taux_implicite"] == 0.2 and tva["plausible"]
    # Taux implausible (0,5 %) → à justifier.
    fec2 = _fec([_l("VT", "20250131", "707000", "0", "10000,00"),
                 _l("VT", "20250131", "445710", "0", "50,00")])
    assert analyser_fec(fec2)["tva"]["plausible"] is False


def test_tva_persistee(client, db_session):
    from app.services import synthese_service
    mid = mission(db_session)
    fec = _fec([_l("VT", "20250131", "707000", "0", "10000,00"),
                _l("VT", "20250131", "445710", "0", "2000,00")])
    client.post(f"/missions/{mid}/vue/fraude/fec",
                files={"fichier": ("fec.txt", fec, "text/plain")},
                data={"seuil": "10000"}, cookies=ck(client))
    ff = synthese_service.collecter(db_session, mid)["fraude_fec"]
    assert ff.tva_applicable and abs(ff.tva_taux_implicite - 0.2) < 1e-6 and ff.tva_plausible


def _la(cpte, aux, deb, cred):
    d = {c: "" for c in _COLS}
    d.update(JournalCode="AC", EcritureDate="20250131", CompteNum=cpte,
             CompAuxNum=aux, Debit=deb, Credit=cred)
    return "\t".join(d[c] for c in _COLS)


def test_tiers_fournisseurs_et_personnel():
    fec = _fec([
        _la("401000", "FRN1", "0", "12345,67"), _la("401000", "FRN1", "0", "8000,50"),
        _la("401000", "FRN2", "0", "2000,00"), _la("401000", "FRN2", "0", "3000,00"),
        _la("401000", "FRN3", "0", "15000,00"),
        _la("421000", "SAL1", "0", "1800,00"), _la("421000", "SAL2", "0", "1800,00"),
        _la("421000", "SAL3", "0", "1800,00"),
    ])
    t = analyser_fec(fec)["tiers"]
    assert t["fournisseurs_nb"] == 3
    assert "FRN2" in t["fournisseurs_ronds"] and "FRN3" in t["fournisseurs_ronds"]
    assert t["fournisseurs_uniques_eleves"] == ["FRN3"]
    assert t["salaries_nb"] == 3 and t["salaires_identiques_partages_nb"] == 1


def test_tiers_persiste(client, db_session):
    from app.services import synthese_service
    mid = mission(db_session)
    fec = _fec([_la("401000", "FRN3", "0", "15000,00"),
                _la("401000", "FRN1", "0", "1234,56")])
    client.post(f"/missions/{mid}/vue/fraude/fec",
                files={"fichier": ("fec.txt", fec, "text/plain")},
                data={"seuil": "10000"}, cookies=ck(client))
    ff = synthese_service.collecter(db_session, mid)["fraude_fec"]
    assert ff.tiers_fournisseurs_nb == 2 and ff.tiers_uniques_eleves_nb == 1


def test_signaux_agreges():
    from app.services.fraude_fec_service import signaux_res
    fec = _fec([_l("BQ", "20250115", "512000", "9500,00", "0"),
                _la("401000", "FRN3", "0", "15000,00")])
    nb, libelles = signaux_res(analyser_fec(fec))
    assert nb >= 2 and "structuration" in libelles


def test_vigilance_affichee_web(client, db_session):
    mid = mission(db_session)
    fec = _fec([_l("BQ", "20250115", "512000", "9500,00", "0"),
                _la("401000", "FRN3", "0", "15000,00")])
    r = client.post(f"/missions/{mid}/vue/fraude/fec",
                    files={"fichier": ("fec.txt", fec, "text/plain")},
                    data={"seuil": "10000"}, cookies=ck(client))
    assert r.status_code == 200 and "Vigilance fraude" in r.text


def test_parite_signaux_ecran_dossier(client, db_session):
    """L'écran (signaux_res) et le dossier (signaux_orm) comptent les mêmes signaux."""
    from app.models.fraude_fec import FraudeFecResultat
    from app.services import fraude_fec_service as F
    mid = mission(db_session)
    fec = _fec([_l("BQ", "20250715", "512000", "0", "9600,00"),
                _la("401000", "FRNX", "0", "25000,00"),
                _la("401000", "FRNR", "0", "2000,00"), _la("401000", "FRNR", "0", "3000,00"),
                _la("421000", "SAL1", "0", "2100,00"), _la("421000", "SAL2", "0", "2100,00"),
                _la("421000", "SAL3", "0", "2100,00")])
    res = F.analyser_fec(fec)
    F.enregistrer(db_session, mid, res, fichier="t.txt")
    ff = (db_session.query(FraudeFecResultat).filter_by(mission_id=mid)
          .order_by(FraudeFecResultat.created_at.desc()).first())
    assert F.signaux_res(res)[0] == F.signaux_orm(ff)[0]
    assert set(F.signaux_res(res)[1]) == set(F.signaux_orm(ff)[1])
