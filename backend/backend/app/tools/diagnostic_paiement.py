"""Diagnostic du paiement : à lancer sur le serveur pour trouver la VRAIE cause d'une erreur de paiement.

    python -m app.tools.diagnostic_paiement

Vérifie la configuration (sans jamais afficher les clés) puis fait un appel de lecture seule chez chaque
fournisseur configuré (aucun paiement créé, aucun débit).
"""
from __future__ import annotations

import httpx

from app.core.config import settings
from app.services import payment_providers as pp


def _ok(msg: str) -> None:
    print(f"  [OK]      {msg}")


def _ko(msg: str) -> None:
    print(f"  [PROBLEME] {msg}")


def _type_cle(cle: str) -> str:
    for p in ("sk_live", "sk_test", "pk_live", "pk_test", "sk_sandbox", "sk_live_", "rk_live", "rk_test"):
        if cle.startswith(p):
            return p
    return "inconnu"


def main() -> None:
    print("== Configuration ==")
    print(f"  Environnement : {settings.environment} | PAYMENT_SANDBOX={settings.payment_sandbox} "
          f"| paiement de test actif : {pp.sandbox_actif()}")
    print(f"  URL du front (retours de paiement) : {settings.frontend_url}")
    if settings.is_production and settings.frontend_url.startswith("http://localhost"):
        _ko("FRONTEND_URL pointe vers localhost en production : les clients seront renvoyés vers une page inexistante.")

    print("\n== Stripe (EUR) ==")
    sk, pk = settings.stripe_secret_key, settings.stripe_publishable_key
    if not sk or not pk:
        _ko("Clés Stripe absentes (STRIPE_SECRET_KEY et STRIPE_PUBLISHABLE_KEY) : le paiement par carte est désactivé.")
    else:
        ts, tp = _type_cle(sk), _type_cle(pk)
        _ok(f"Clés présentes (secrète : {ts}…, publique : {tp}…)")
        if ts.split("_")[1:2] != tp.split("_")[1:2]:
            _ko("Clé secrète et clé publique ne sont pas du même mode (test/live) : Stripe refusera le paiement.")
        try:
            r = httpx.get("https://api.stripe.com/v1/balance", auth=(sk, ""), timeout=20)
            if r.status_code == 200:
                _ok("Stripe accepte la clé secrète.")
            else:
                _ko(f"Stripe répond HTTP {r.status_code} : {r.text[:300]}")
        except httpx.HTTPError as exc:
            _ko(f"Stripe injoignable depuis ce serveur ({exc.__class__.__name__}) : pare-feu / DNS / accès sortant ?")

    print("\n== FedaPay (XOF) ==")
    fk = settings.fedapay_secret_key
    if not fk:
        _ko("FEDAPAY_SECRET_KEY absente : Mobile Money / cartes XOF désactivés.")
    else:
        _ok(f"Clé présente ({_type_cle(fk)}…), environnement {settings.fedapay_env}")
        if settings.fedapay_env == "live" and "sandbox" in fk:
            _ko("Clé « sandbox » avec FEDAPAY_ENV=live : incohérent.")
        if settings.fedapay_env != "live" and fk.startswith("sk_live"):
            _ko("Clé live avec un environnement non « live » : incohérent.")
        try:
            r = httpx.get(f"{pp._fedapay_base()}/transactions?per_page=1",
                          headers={"Authorization": f"Bearer {fk}"}, timeout=20)
            if r.status_code == 200:
                _ok("FedaPay accepte la clé secrète.")
            else:
                _ko(f"FedaPay répond HTTP {r.status_code} : {r.text[:300]}")
        except httpx.HTTPError as exc:
            _ko(f"FedaPay injoignable depuis ce serveur ({exc.__class__.__name__}).")

    print("\n== Virement ==")
    if pp.virement_configure():
        _ok("Coordonnées bancaires renseignées.")
        if "..." in settings.virement_iban or "..." in settings.virement_banque:
            _ko("L'IBAN ou la banque contient encore « ... » (valeur d'exemple) : renseignez les vraies coordonnées.")
    else:
        _ko("Coordonnées de virement absentes (VIREMENT_TITULAIRE / VIREMENT_IBAN).")


if __name__ == "__main__":
    main()
