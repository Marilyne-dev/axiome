"""Accès à Supabase (PostgreSQL en ligne) via l'API officielle supabase-py.
La clé SECRÈTE reste côté backend : elle ne doit JAMAIS aller dans le frontend."""
import os
from functools import lru_cache

from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client, create_client


@lru_cache
def client() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = (os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        raise HTTPException(
            status_code=503,
            detail="Supabase n'est pas configuré : renseignez SUPABASE_URL et SUPABASE_SECRET_KEY dans backend/.env",
        )
    return create_client(url, key)


def _run(fn):
    try:
        return fn()
    except APIError as e:
        raise HTTPException(status_code=502, detail=f"Erreur base de données : {e.message}")


def ping():
    _run(lambda: client().table("users").select("id").limit(1).execute())


def create_user(email: str, name: str, firm: str, password_hash: str) -> dict:
    try:
        res = client().table("users").insert(
            {"email": email, "name": name, "firm": firm, "password_hash": password_hash}
        ).execute()
    except APIError as e:
        if e.code == "23505":  # violation d'unicité
            raise HTTPException(status_code=409, detail="Un compte existe déjà avec cet e-mail.")
        raise HTTPException(status_code=502, detail=f"Erreur base de données : {e.message}")
    return res.data[0]


def get_user_by_email(email: str) -> dict | None:
    res = _run(lambda: client().table("users").select("*").eq("email", email).limit(1).execute())
    return res.data[0] if res.data else None


def get_user_by_id(user_id: int) -> dict | None:
    res = _run(lambda: client().table("users").select("*").eq("id", user_id).limit(1).execute())
    return res.data[0] if res.data else None


def insert_demo(payload: dict) -> None:
    _run(lambda: client().table("demo_requests").insert(payload).execute())
