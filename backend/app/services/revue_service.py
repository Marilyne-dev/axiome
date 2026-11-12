"""Module 15 — Revue analytique : comparaison N / N-1 et détection des variations
significatives (au-delà du seuil de remontée d'anomalie)."""
from __future__ import annotations

from app.models.balance import LigneBalance


def revue_analytique(lignes: list[LigneBalance], seuil: float = 0.0) -> dict:
    """Compare N et N-1 par compte, calcule variation absolue et relative, et
    signale les écarts > seuil (en valeur absolue)."""
    resultats = []
    for lb in sorted(lignes, key=lambda x: x.compte):
        var = round(lb.solde_n - lb.solde_n1, 2)
        pct = round(var / abs(lb.solde_n1), 4) if lb.solde_n1 else None
        significatif = seuil > 0 and abs(var) >= seuil
        resultats.append({
            "compte": lb.compte, "libelle": lb.libelle,
            "solde_n": round(lb.solde_n, 2), "solde_n1": round(lb.solde_n1, 2),
            "variation": var, "variation_pct": pct, "significatif": significatif,
        })
    nb_signif = sum(1 for r in resultats if r["significatif"])
    return {"seuil_applique": seuil, "nb_comptes": len(resultats),
            "nb_significatifs": nb_signif, "lignes": resultats}
