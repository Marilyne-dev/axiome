"""Tests devises : présence du référentiel ISO 4217 + conversion."""
from __future__ import annotations

import pytest

from app.models.devise import Devise, TauxDeChange
from app.services.devise_service import DeviseInconnue, convertir


def test_devises_iso_chargees(db_session):
    codes = {d.code for d in db_session.query(Devise).all()}
    assert {"EUR", "USD", "XOF"} <= codes           # jeu ISO présent
    assert db_session.query(Devise).count() >= 50   # pycountry ou repli


def test_conversion_avec_taux(db_session):
    db_session.add(TauxDeChange(source="EUR", cible="USD", taux=1.10))
    db_session.flush()
    assert convertir(db_session, 100, "EUR", "USD") == pytest.approx(110.0)


def test_conversion_identite(db_session):
    assert convertir(db_session, 42, "EUR", "EUR") == 42


def test_devise_inconnue(db_session):
    with pytest.raises(DeviseInconnue):
        convertir(db_session, 1, "ZZZ", "EUR")
