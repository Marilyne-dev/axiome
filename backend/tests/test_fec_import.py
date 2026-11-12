"""Module 5 — import FEC : parsing, classification PCG, persistance, web."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.core.cycles_ref import cycle_pour_cs
from app.core.pcg_cycles import cs_standard_pour_compte
from app.models.balance import LigneBalance
from app.services import fec_import_service
from app.services.fec_service import parser_fec

_COLS = ("JournalCode", "JournalLib", "EcritureNum", "EcritureDate", "CompteNum",
         "CompteLib", "CompAuxNum", "CompAuxLib", "PieceRef", "PieceDate",
         "EcritureLib", "Debit", "Credit", "EcritureLet", "DateLet",
         "ValidDate", "Montantdevise", "Idevise")


def _ligne(compte, lib, debit, credit, sep="\t"):
    d = {c: "" for c in _COLS}
    d.update(CompteNum=compte, CompteLib=lib, Debit=debit, Credit=credit, EcritureDate="20250131")
    return sep.join(d[c] for c in _COLS)


def _fec(lignes, sep="\t"):
    return "\n".join([sep.join(_COLS), *lignes])


# ---- Parser ---------------------------------------------------------------

def test_parser_equilibre_et_agregats():
    fec = _fec([
        _ligne("512000", "Banque", "10 000,00", "0"),
        _ligne("101000", "Capital", "0", "10 000,00"),
        _ligne("707000", "Ventes", "0", "1 000,00"),
        _ligne("411000", "Clients", "1 000,00", "0"),
    ])
    res = parser_fec(fec)
    assert res.equilibre                       # Σ débit = Σ crédit
    assert res.chiffre_affaires == 1000.0
    assert res.capitaux_propres == 10000.0
    # Débit/crédit conservés par compte.
    banque = next(l for l in res.lignes if l.compte == "512000")
    assert banque.debit == 10000.0 and banque.credit == 0.0


def test_parser_formats_montants_et_pipe():
    # Séparateur pipe + montants au format point.
    fec = _fec([_ligne("512000", "Banque", "1234.56", "0", sep="|"),
                _ligne("101000", "Capital", "0", "1234.56", sep="|")], sep="|")
    res = parser_fec(fec)
    assert res.total_debit == 1234.56 and res.equilibre


def test_parser_desequilibre():
    fec = _fec([_ligne("512000", "Banque", "100", "0")])
    assert parser_fec(fec).equilibre is False


# ---- Classification PCG ---------------------------------------------------

def test_classification_pcg():
    attendu = {
        "101000": "FONDS_PROPRES", "164000": "EMPRUNTS", "218300": "IMMO_CORP",
        "271000": "IMMO_FI", "370000": "STOCKS", "411000": "CLIENTS",
        "401000": "FOURNISSEURS", "421000": "PERSONNEL", "445660": "IMPOTS",
        "455000": "AFFILIES", "512000": "TRESORERIE", "606000": "AUTRES",
    }
    for compte, cycle in attendu.items():
        assert cycle_pour_cs(cs_standard_pour_compte(compte)) == cycle, compte


# ---- Import persistant ----------------------------------------------------

def test_import_fec_persiste_et_classe(db_session):
    mid = mission(db_session)
    fec = _fec([
        _ligne("512000", "Banque", "10000", "0"),
        _ligne("101000", "Capital", "0", "10000"),
        _ligne("411000", "Clients", "1200", "0"),
        _ligne("445710", "TVA", "0", "1200"),
    ])
    res = fec_import_service.importer_fec(db_session, mid, fec)
    assert res["nb_comptes"] == 4 and res["equilibre"]
    lignes = db_session.query(LigneBalance).filter_by(mission_id=mid).all()
    cycles = {lb.compte: cycle_pour_cs(lb.cs_standard) for lb in lignes}
    assert cycles["512000"] == "TRESORERIE" and cycles["445710"] == "IMPOTS"
    # Idempotent : réimporter remplace, ne cumule pas.
    fec_import_service.importer_fec(db_session, mid, fec)
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 4


# ---- Web ------------------------------------------------------------------

def test_upload_fec_web(client, db_session):
    mid = mission(db_session)
    fec = _fec([_ligne("512000", "Banque", "10000", "0"),
                _ligne("101000", "Capital", "0", "10000")])
    r = client.post(f"/missions/{mid}/fec-import",
                    files={"fichier": ("fec.txt", fec, "text/plain")},
                    cookies=ck(client), follow_redirects=False)
    assert r.status_code == 302
    assert "fec=ok" in r.headers["location"] and "equilibre=1" in r.headers["location"]
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 2


def test_upload_fec_garde_fou_remplacement(client, db_session):
    mid = mission(db_session)
    fec = _fec([_ligne("512000", "Banque", "10000", "0"),
                _ligne("101000", "Capital", "0", "10000")])
    up = {"fichier": ("fec.txt", fec, "text/plain")}
    # 1er import (balance vide) : autorisé sans confirmation.
    r1 = client.post(f"/missions/{mid}/fec-import", files=up, cookies=ck(client), follow_redirects=False)
    assert "fec=ok" in r1.headers["location"]
    # 2e import sans confirmer : bloqué (balance existante préservée).
    r2 = client.post(f"/missions/{mid}/fec-import", files=up, cookies=ck(client), follow_redirects=False)
    assert "fec=confirm" in r2.headers["location"]
    # 2e import avec confirmer : autorisé, pas de doublon.
    r3 = client.post(f"/missions/{mid}/fec-import", data={"confirmer": "1"}, files=up,
                     cookies=ck(client), follow_redirects=False)
    assert "fec=ok" in r3.headers["location"]
    assert db_session.query(LigneBalance).filter_by(mission_id=mid).count() == 2
