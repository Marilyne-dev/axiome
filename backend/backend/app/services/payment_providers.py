"""Fournisseurs de paiement : Stripe (carte, prélèvement SEPA), FedaPay (Mobile Money, cartes),
virement bancaire et mode test.

Principe de sécurité : on ne fait JAMAIS confiance à une notification reçue ni au navigateur.
Pour activer un espace, on interroge directement le fournisseur avec notre clé secrète et on lit
le statut réel. Les numéros de carte / IBAN sont saisis dans les champs sécurisés de Stripe
(iframe) : ils ne transitent jamais par nos serveurs (hors périmètre PCI-DSS lourd).
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("axiome.paiement")

# Opérateurs Mobile Money acceptés SANS redirection (API directe FedaPay) : code -> (libellé, pays ISO).
OPERATEURS_DIRECTS = {
    "mtn": ("MTN Mobile Money Bénin", "bj"),
    "moov": ("Moov Money Bénin", "bj"),
    "mtn_ci": ("MTN Mobile Money Côte d'Ivoire", "ci"),
    "moov_tg": ("Moov Money Togo", "tg"),
}


class ErreurPaiement(Exception):
    """Paiement impossible (fournisseur indisponible ou non configuré)."""


def _erreur_fournisseur(nom: str, exc: httpx.HTTPError) -> ErreurPaiement:
    """Journalise la VRAIE cause (code HTTP + réponse du fournisseur, jamais les clés) et renvoie un message clair.

    Avant, toute erreur devenait « service momentanément indisponible », ce qui masquait une clé invalide,
    une devise refusée ou un montant sous le minimum du fournisseur.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        corps = exc.response.text[:500]
        logger.error("%s : HTTP %s — %s", nom, code, corps)
        if code in (401, 403):
            return ErreurPaiement(f"{nom} refuse la clé API configurée (HTTP {code}). Vérifiez les clés du serveur.")
        if code in (400, 402, 422):
            return ErreurPaiement(f"{nom} a refusé la demande de paiement (HTTP {code}). Consultez les journaux du serveur.")
        return ErreurPaiement(f"{nom} est momentanément indisponible (HTTP {code}). Réessayez.")
    logger.error("%s : connexion impossible — %s", nom, exc.__class__.__name__)
    return ErreurPaiement(f"Impossible de joindre {nom} ({exc.__class__.__name__}). Vérifiez la connexion du serveur.")


def sandbox_actif() -> bool:
    return settings.payment_sandbox and not settings.is_production


def virement_configure() -> bool:
    return bool(settings.virement_iban and settings.virement_titulaire)


def methodes_disponibles(devise: str) -> list[dict]:
    """Moyens de paiement réellement utilisables pour cette devise (selon les clés configurées)."""
    m: list[dict] = []
    if devise == "EUR":
        if settings.stripe_secret_key and settings.stripe_publishable_key:
            m.append({"code": "stripe", "libelle": "Carte bancaire ou prélèvement SEPA",
                      "detail": "Visa, Mastercard, CB, IBAN — saisie sécurisée par Stripe"})
    else:
        if settings.fedapay_secret_key:
            m.append({"code": "mobile_money", "libelle": "Mobile Money",
                      "detail": "MTN, Moov : validation sur votre téléphone", "operateurs": [
                          {"code": c, "libelle": v[0], "pays": v[1]} for c, v in OPERATEURS_DIRECTS.items()]})
            m.append({"code": "fedapay", "libelle": "Carte bancaire / autres Mobile Money",
                      "detail": "Visa, Mastercard, Celtiis, Orange, Wave… sur la page sécurisée FedaPay"})
    if virement_configure():
        m.append({"code": "virement", "libelle": "Virement bancaire",
                  "detail": "Activation à réception du virement (24 à 48 h ouvrées)"})
    return m


def _fedapay_base() -> str:
    return "https://api.fedapay.com/v1" if settings.fedapay_env == "live" else "https://sandbox-api.fedapay.com/v1"


def _retour(reference: str, **extra: str) -> str:
    q = "&".join([f"ref={reference}"] + [f"{k}={v}" for k, v in extra.items()])
    return f"{settings.frontend_url.rstrip('/')}/paiement/retour?{q}"


def url_paiement(reference: str) -> str:
    """Page de paiement AXIOME où le payeur choisit son moyen de paiement."""
    return f"{settings.frontend_url.rstrip('/')}/paiement/{reference}"


# ------------------------------------------------------------------ Stripe
def stripe_creer_intention(*, reference: str, montant: int, devise: str, libelle: str, email: str) -> tuple[str, str]:
    """PaymentIntent avec moyens de paiement automatiques (carte, SEPA…). -> (id, client_secret)."""
    if not (settings.stripe_secret_key and settings.stripe_publishable_key):
        raise ErreurPaiement("Le paiement par carte n'est pas encore activé. Contactez AXIOME.")
    data = {"amount": str(montant), "currency": devise.lower(), "automatic_payment_methods[enabled]": "true",
            "description": libelle, "receipt_email": email, "metadata[reference]": reference}
    try:
        with httpx.Client(timeout=20) as http:
            r = http.post("https://api.stripe.com/v1/payment_intents", data=data, auth=(settings.stripe_secret_key, ""),
                          headers={"Idempotency-Key": f"pi-{reference}"})
            r.raise_for_status()
            j = r.json()
            return j["id"], j["client_secret"]
    except httpx.HTTPError as exc:
        raise _erreur_fournisseur("Stripe", exc) from exc


# ------------------------------------------------------------------ FedaPay
def _fedapay_transaction(http: httpx.Client, *, reference: str, montant: int, devise: str, libelle: str,
                         email: str, nom: str, tel: dict | None = None) -> tuple[str, str, str]:
    """Crée la transaction FedaPay et son jeton. -> (id transaction, jeton, URL de la page de paiement)."""
    h = {"Authorization": f"Bearer {settings.fedapay_secret_key}"}
    prenom, _, reste = nom.partition(" ")
    client = {"firstname": prenom or nom, "lastname": reste or prenom or nom, "email": email}
    if tel:
        client["phone_number"] = tel
    body = {"description": libelle, "amount": montant, "currency": {"iso": devise},
            "callback_url": _retour(reference), "customer": client, "merchant_reference": reference}
    r = http.post(f"{_fedapay_base()}/transactions", json=body, headers=h)
    r.raise_for_status()
    j = r.json()
    tx = j.get("v1/transaction") or j.get("transaction") or j
    tid = str(tx["id"])
    t = http.post(f"{_fedapay_base()}/transactions/{tid}/token", headers=h)
    t.raise_for_status()
    tj = t.json()
    token = tj.get("token") or (tj.get("v1/token") or {}).get("token")
    url = tj.get("url") or (tj.get("v1/token") or {}).get("url")
    return tid, (token or ""), (url or "")


def fedapay_lien(*, reference: str, montant: int, devise: str, libelle: str, email: str, nom: str) -> tuple[str, str]:
    """Page sécurisée FedaPay (cartes + tous les Mobile Money). -> (id transaction, URL)."""
    try:
        with httpx.Client(timeout=20) as http:
            tid, _token, url = _fedapay_transaction(http, reference=reference, montant=montant, devise=devise,
                                                    libelle=libelle, email=email, nom=nom)
    except httpx.HTTPError as exc:
        raise _erreur_fournisseur("FedaPay", exc) from exc
    if not url:
        raise ErreurPaiement("Réponse FedaPay inattendue.")
    return tid, url


def fedapay_mobile_money(*, reference: str, montant: int, devise: str, libelle: str, email: str, nom: str,
                         operateur: str, numero: str) -> str:
    """Paiement Mobile Money sans redirection : le client reçoit la demande sur son téléphone. -> id transaction."""
    if operateur not in OPERATEURS_DIRECTS:
        raise ErreurPaiement("Opérateur Mobile Money non pris en charge.")
    pays = OPERATEURS_DIRECTS[operateur][1]
    chiffres = "".join(c for c in numero if c.isdigit())
    if not 8 <= len(chiffres) <= 13:
        raise ErreurPaiement("Numéro de téléphone invalide.")
    tel = {"number": chiffres, "country": pays}
    try:
        with httpx.Client(timeout=30) as http:
            tid, token, _url = _fedapay_transaction(http, reference=reference, montant=montant, devise=devise,
                                                    libelle=libelle, email=email, nom=nom, tel=tel)
            if not token:
                raise ErreurPaiement("Réponse FedaPay inattendue.")
            r = http.post(f"{_fedapay_base()}/{operateur}", json={"token": token, "phone_number": tel},
                          headers={"Authorization": f"Bearer {settings.fedapay_secret_key}"})
            r.raise_for_status()
            return tid
    except httpx.HTTPError as exc:
        raise _erreur_fournisseur("FedaPay", exc) from exc


# ------------------------------------------------------------------ vérification (source de vérité)
def verifier(fournisseur: str, fournisseur_ref: str) -> str:
    """Statut réel auprès du fournisseur : 'paye' | 'echoue' | 'en_attente'."""
    if fournisseur == "test":
        return "paye" if fournisseur_ref == "confirme" else "en_attente"
    if fournisseur == "virement":
        return "paye" if fournisseur_ref == "recu" else "en_attente"      # posé uniquement par l'éditeur
    try:
        with httpx.Client(timeout=20) as http:
            if fournisseur == "stripe":
                if fournisseur_ref.startswith("pi_"):
                    r = http.get(f"https://api.stripe.com/v1/payment_intents/{fournisseur_ref}", auth=(settings.stripe_secret_key, ""))
                    r.raise_for_status()
                    st = r.json().get("status")
                    if st == "succeeded":
                        return "paye"
                    return "echoue" if st == "canceled" else "en_attente"   # « processing » = SEPA en cours
                r = http.get(f"https://api.stripe.com/v1/checkout/sessions/{fournisseur_ref}", auth=(settings.stripe_secret_key, ""))
                r.raise_for_status()
                j = r.json()
                if j.get("payment_status") == "paid":
                    return "paye"
                return "echoue" if j.get("status") == "expired" else "en_attente"
            if fournisseur == "fedapay":
                r = http.get(f"{_fedapay_base()}/transactions/{fournisseur_ref}",
                             headers={"Authorization": f"Bearer {settings.fedapay_secret_key}"})
                r.raise_for_status()
                j = r.json()
                tx = j.get("v1/transaction") or j.get("transaction") or j
                st = str(tx.get("status", "")).lower()
                if st in ("approved", "transferred"):
                    return "paye"
                return "echoue" if st in ("declined", "canceled", "cancelled", "refunded") else "en_attente"
    except httpx.HTTPError:
        return "en_attente"   # en cas de doute on n'active JAMAIS : le prochain contrôle tranchera
    return "en_attente"
