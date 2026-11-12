"""Source de vérité des devises ISO 4217.

Approche robuste : on lit la liste officielle via `pycountry` (jeu complet,
maintenu). Repli sur une liste des principales devises si pycountry est absent,
afin que le seed ne casse jamais. Aucune devise n'est ainsi codée en dur dans
la logique métier — elle vit en base (table Devise) après chargement.
"""
from __future__ import annotations

# Symboles usuels (facultatif : purement cosmétique pour l'UI).
_SYMBOLS: dict[str, str] = {
    "EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF", "CNY": "¥",
    "XOF": "CFA", "XAF": "FCFA", "MAD": "DH", "TND": "DT", "DZD": "DA",
    "CAD": "$", "AUD": "$", "INR": "₹", "BRL": "R$", "ZAR": "R", "NGN": "₦",
}

# Repli minimal si pycountry indisponible (le seed reste fonctionnel).
_FALLBACK: list[tuple[str, str, int]] = [
    ("EUR", "Euro", 2), ("USD", "US Dollar", 2), ("GBP", "Pound Sterling", 2),
    ("JPY", "Yen", 0), ("CHF", "Swiss Franc", 2), ("CNY", "Yuan Renminbi", 2),
    ("XOF", "CFA Franc BCEAO", 0), ("XAF", "CFA Franc BEAC", 0),
    ("MAD", "Moroccan Dirham", 2), ("CAD", "Canadian Dollar", 2),
    ("AUD", "Australian Dollar", 2), ("INR", "Indian Rupee", 2),
]


def iter_iso4217() -> list[dict]:
    """Retourne la liste des devises à insérer : {code, libelle, symbole, decimales}."""
    devises: list[dict] = []
    try:
        import pycountry  # import paresseux

        for cur in pycountry.currencies:
            code = getattr(cur, "alpha_3", None)
            name = getattr(cur, "name", None)
            if not code or not name:
                continue
            devises.append({
                "code": code,
                "libelle": name,
                "symbole": _SYMBOLS.get(code, ""),
                "decimales": 2,  # défaut ISO usuel ; ajustable par devise si besoin
            })
    except Exception:  # noqa: BLE001 — repli volontaire
        for code, name, dec in _FALLBACK:
            devises.append({"code": code, "libelle": name, "symbole": _SYMBOLS.get(code, ""), "decimales": dec})
    return devises
