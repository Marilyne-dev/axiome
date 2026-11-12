"""Test de l'invariant de cloisonnement multi-référentiel."""
from __future__ import annotations

import pytest

from app.models.cabinet import Cabinet
from app.models.client import Client
from app.models.mission import Mission
from app.models.referentiel import RegleFiscale
from app.services.referentiel_service import (
    ReferentielViolation,
    appliquer_regle,
    regles_applicables,
)


def _mission(db, referentiel, pays):
    cab = Cabinet(nom="Cab Test", pays=pays)
    db.add(cab); db.flush()
    c = Client(cabinet_id=cab.id, raison_sociale="X", pays=pays)
    db.add(c); db.flush()
    m = Mission(client_id=c.id, intitule="M", referentiel=referentiel, pays=pays, devise="EUR")
    db.add(m); db.flush()
    return m


def test_regle_pcg_interdite_sur_mission_syscohada(db_session):
    m = _mission(db_session, "SYSCOHADA_OHADA", "Côte d'Ivoire")
    regle_pcg = RegleFiscale(referentiel_code="PCG_FR", pays="France", code="TVA_NORMALE", taux=0.20)
    with pytest.raises(ReferentielViolation):
        appliquer_regle(m, regle_pcg)


def test_regles_applicables_filtrees_par_referentiel(db_session):
    # Les règles PCG_FR/France et SYSCOHADA/CI sont déjà chargées par le seed de test.
    m = _mission(db_session, "PCG_FR", "France")
    regles = regles_applicables(db_session, m)
    assert regles and all(r.referentiel_code == "PCG_FR" and r.pays == "France" for r in regles)
