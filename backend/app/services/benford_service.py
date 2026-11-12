"""Module 13 — Détection de fraude : loi de Benford et indicateurs complémentaires.

La loi de Benford donne la fréquence attendue du premier chiffre significatif :
P(d) = log10(1 + 1/d). Un écart marqué peut signaler une manipulation, mais
reste une PISTE : l'auditeur investigue, l'outil ne conclut jamais seul.
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable

# Fréquences théoriques de Benford pour le 1er chiffre (1..9).
BENFORD = {d: math.log10(1 + 1 / d) for d in range(1, 10)}

# Seuils MAD (Mean Absolute Deviation) de Nigrini pour le 1er chiffre.
_SEUILS_MAD = [
    (0.006, "conformité proche"),
    (0.012, "conformité acceptable"),
    (0.015, "conformité marginale"),
    (float("inf"), "non-conformité"),
]


def _premier_chiffre(x: float) -> int | None:
    x = abs(x)
    if x < 1:
        # décaler jusqu'au premier chiffre significatif
        while 0 < x < 1:
            x *= 10
    if x == 0:
        return None
    d = int(str(int(x))[0])
    return d if 1 <= d <= 9 else None


def analyse_benford(montants: Iterable[float]) -> dict:
    """Analyse Benford du 1er chiffre : distribution observée vs théorique, MAD, khi²."""
    chiffres = [d for m in montants if (d := _premier_chiffre(m)) is not None]
    n = len(chiffres)
    if n == 0:
        return {"n": 0, "exploitable": False, "message": "Aucun montant exploitable."}

    obs = Counter(chiffres)
    distribution = []
    mad = 0.0
    khi2 = 0.0
    for d in range(1, 10):
        freq_obs = obs.get(d, 0) / n
        freq_att = BENFORD[d]
        ecart = abs(freq_obs - freq_att)
        mad += ecart
        attendu_n = freq_att * n
        if attendu_n:
            khi2 += (obs.get(d, 0) - attendu_n) ** 2 / attendu_n
        distribution.append({
            "chiffre": d, "observe": round(freq_obs, 4), "attendu": round(freq_att, 4),
            "ecart": round(ecart, 4), "nb": obs.get(d, 0),
        })
    mad /= 9

    conformite = next(lib for seuil, lib in _SEUILS_MAD if mad <= seuil)
    # valeur critique khi² à 8 ddl, seuil 5 % = 15.507
    return {
        "n": n, "exploitable": True, "mad": round(mad, 5), "conformite": conformite,
        "khi2": round(khi2, 3), "khi2_critique_5pct": 15.507,
        "suspicion": khi2 > 15.507 or mad > 0.015,
        "distribution": distribution,
    }


def indicateurs_fraude(montants: list[float]) -> dict:
    """Indicateurs complémentaires : nombres ronds, montants dupliqués."""
    montants = [m for m in montants if m]
    n = len(montants)
    if n == 0:
        return {"n": 0}
    ronds = sum(1 for m in montants if abs(m) >= 1000 and round(abs(m)) % 1000 == 0)
    compte = Counter(round(abs(m), 2) for m in montants)
    doublons = {v: c for v, c in compte.items() if c > 1}
    return {
        "n": n,
        "nombres_ronds": ronds,
        "part_nombres_ronds": round(ronds / n, 4),
        "nb_montants_dupliques": len(doublons),
        "top_doublons": sorted(doublons.items(), key=lambda x: -x[1])[:5],
    }
