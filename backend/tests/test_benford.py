"""Module 13 — loi de Benford et indicateurs de fraude."""
from __future__ import annotations

from app.services.benford_service import BENFORD, analyse_benford, indicateurs_fraude


def _jeu_conforme() -> list[float]:
    """Construit un jeu dont le 1er chiffre suit exactement Benford."""
    montants = []
    for d in range(1, 10):
        for _ in range(round(1000 * BENFORD[d])):
            montants.append(float(f"{d}23"))   # 1er chiffre = d
    return montants


def test_benford_conforme():
    res = analyse_benford(_jeu_conforme())
    assert res["exploitable"] and res["suspicion"] is False
    assert res["mad"] <= 0.006  # conformité proche


def test_benford_manipule():
    # tous les montants commencent par 5 -> forte non-conformité
    res = analyse_benford([500 + i for i in range(200)])
    assert res["suspicion"] is True and res["mad"] > 0.015


def test_indicateurs_ronds_et_doublons():
    res = indicateurs_fraude([1000, 2000, 3000, 1234.5, 1234.5, 1234.5, 777])
    assert res["nombres_ronds"] == 3
    assert res["nb_montants_dupliques"] == 1  # 1234.5 en doublon
