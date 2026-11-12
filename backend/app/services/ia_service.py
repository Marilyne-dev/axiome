"""Modules 14/16 — Assistant IA (API Anthropic Claude).

L'IA assiste la rédaction/synthèse ; elle ne se substitue jamais au jugement du
commissaire aux comptes. La clé API provient de l'environnement (jamais en dur).
Si aucune clé n'est configurée, le service se dégrade proprement.
"""
from __future__ import annotations

import httpx

from app.core.config import settings

_API_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-sonnet-4-6"
_SYSTEM = (
    "Tu es l'assistant d'AXIOME, plateforme d'audit légal. Tu aides le commissaire "
    "aux comptes à rédiger et synthétiser (notes, revues, conclusions) dans le respect "
    "des normes (NEP/ISA). Tu proposes, tu n'affirmes jamais de conclusion d'audit : "
    "la décision et la signature restent celles du professionnel."
)


def ia_disponible() -> bool:
    return bool(settings.anthropic_api_key)


def assister(prompt: str, contexte: str = "", max_tokens: int = 800) -> dict:
    """Interroge Claude pour une aide rédactionnelle. Dégradé si non configuré."""
    if not ia_disponible():
        return {"disponible": False,
                "message": "Assistant IA non configuré (ANTHROPIC_API_KEY absente).",
                "reponse": ""}
    contenu = f"{contexte}\n\n{prompt}" if contexte else prompt
    try:
        r = httpx.post(
            _API_URL,
            headers={"x-api-key": settings.anthropic_api_key,
                     "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": _MODEL, "max_tokens": max_tokens, "system": _SYSTEM,
                  "messages": [{"role": "user", "content": contenu}]},
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        texte = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return {"disponible": True, "reponse": texte,
                "avertissement": "Proposition de l'IA — à valider par le professionnel."}
    except Exception as exc:  # noqa: BLE001 — dégradation gracieuse
        return {"disponible": True, "erreur": str(exc), "reponse": ""}
