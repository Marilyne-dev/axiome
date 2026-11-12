"""API AXIOME — FastAPI + Supabase (PostgreSQL en ligne).
Lancer : uvicorn main:app --reload --port 8000
Docs interactives : http://localhost:8000/docs
"""
import re
from datetime import datetime, timezone

import jwt
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()  # lit backend/.env

import db  # noqa: E402  (après load_dotenv)
from auth import create_token, decode_token, hash_password, verify_password  # noqa: E402

app = FastAPI(title="AXIOME API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EMAIL_RE = r"[^@\s]+@[^@\s]+\.[^@\s]+"

# ---------------------------------------------------------------- contenu
CONTENT = {
    "standards": [
        {"tag": "NEP", "label": "Normes d'exercice professionnel"},
        {"tag": "ISA", "label": "200–720"},
        {"tag": "IA ACT", "label": "Règl. (UE) 2024/1689"},
        {"tag": "LCB-FT", "label": "CMF · TRACFIN"},
        {"tag": "RGPD", "label": "Règl. (UE) 2016/679"},
    ],
    "modules": [
        {"id": "analytics", "num": "01", "name": "ANALYTICS",
         "title": "Documents prêts à l'emploi",
         "text": "Exploitez le FEC et la DSN pour produire analyses, papiers de travail, synthèses et supports de restitution."},
        {"id": "platform", "num": "02", "name": "PLATEFORME",
         "title": "Le dossier d'audit, de bout en bout",
         "text": "Structurez et documentez le dossier : acceptation, planification, réalisation, finalisation — avec la conformité réglementaire intégrée."},
        {"id": "link", "num": "03", "name": "LINK",
         "title": "Add-in Excel pour l'audit",
         "text": "Importez, organisez et référencez les justificatifs directement depuis vos papiers de travail."},
    ],
    "outputs": [
        {"logo": "BI", "color": "#E0A100", "tool": "Power BI", "title": "Rapport interactif",
         "text": "100+ pages d'analyses organisées par cycle, pensées pour les dossiers volumineux."},
        {"logo": "XL", "color": "#1E7145", "tool": "Excel", "title": "Papiers de travail",
         "text": "Procédures automatisées et précomplétées, prêtes pour le dossier (pack WAUX)."},
        {"logo": "W", "color": "#1B49C4", "tool": "Word", "title": "Revue analytique",
         "text": "Document généré et commenté, structuré selon les exigences professionnelles (NEP 520)."},
        {"logo": "P", "color": "#C0392B", "tool": "PowerPoint", "title": "Support de restitution",
         "text": "Trame préformatée intégrant analyses et visuels clés pour standardiser la restitution."},
    ],
    "plans": [
        {"name": "Analytics", "featured": False,
         "desc": "Pour fiabiliser les analyses et produire les papiers de travail.",
         "price": "Sur devis",
         "features": ["Analyse FEC / DSN + détection ML", "Pack de papiers de travail (WAUX)",
                      "Revue analytique commentée", "Exports Power BI · Excel · Word · PPT"]},
        {"name": "Suite complète", "featured": True,
         "desc": "Analytics + Plateforme + Link, l'écosystème intégré.",
         "price": "Sur devis",
         "features": ["Les trois modules réunis", "Conformité IA Act · LCB-FT · RGPD",
                      "Portail collaborateurs & commissaires aux comptes",
                      "Support prioritaire & mises à jour NEP"]},
        {"name": "Plateforme", "featured": False,
         "desc": "Pour structurer et documenter le dossier de bout en bout.",
         "price": "Sur devis",
         "features": ["Acceptation → finalisation", "Questionnaires alignés NEP",
                      "Cartographie des risques", "API INSEE · INPI · BODACC"]},
    ],
    "faq": [
        {"q": "La suite est-elle conforme aux NEP et aux normes ISA ?",
         "a": "Oui. La méthodologie suit les Normes d'Exercice Professionnel (dont les NEP 315 et 330 révisées) et les normes ISA 200 à 720. Les conclusions et l'opinion restent celles du commissaire aux comptes."},
        {"q": "Comment sont protégées les données comptables ?",
         "a": "Les traitements respectent le RGPD : chiffrement, gestion des accès, traçabilité et durées de conservation définies. Aucune réutilisation à d'autres fins."},
        {"q": "Quelle est l'approche vis-à-vis de l'IA Act ?",
         "a": "Le système est positionné comme une aide à la décision sous contrôle humain. Un module dédié classe l'usage au regard du Règlement (UE) 2024/1689."},
        {"q": "Les modules sont-ils utilisables séparément ?",
         "a": "Oui. Analytics, Plateforme et Link sont souscriptibles indépendamment ou ensemble."},
        {"q": "Quels formats de données sont pris en charge ?",
         "a": "Le FEC (format A47), les balances N/N-1, les grands livres et la DSN, ainsi que les exports Excel/CSV usuels."},
    ],
}


# ---------------------------------------------------------------- modèles
class DemoRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=200)
    firm: str = Field(default="", max_length=120)
    message: str = Field(default="", max_length=1000)


class ReconcileInput(BaseModel):
    ca: float = Field(ge=0, description="Chiffre d'affaires de l'exercice")
    encaissements: float = Field(ge=0, description="Encaissements constatés")
    creances_n: float = Field(ge=0, description="Créances clients clôture N")
    creances_n1: float = Field(ge=0, description="Créances clients clôture N-1")
    factures_a_etablir: float = Field(default=0, ge=0)
    seuil_pct: float = Field(default=1.0, ge=0, le=100, description="Seuil d'écart atypique (%)")


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=200)
    firm: str = Field(default="", max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------- routes générales
@app.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/health/db")
def health_db():
    """Vérifie la connexion à Supabase (utile pour tester vos clés)."""
    db.ping()
    return {"status": "ok", "database": "supabase"}


@app.get("/api/content")
def content():
    return CONTENT


@app.post("/api/analytics/reconcile")
def reconcile(data: ReconcileInput):
    """Encaissements attendus = CA − créances N + créances N-1 − factures à établir.
    L'écart est atypique s'il dépasse le seuil (en % du CA)."""
    attendus = data.ca - data.creances_n + data.creances_n1 - data.factures_a_etablir
    ecart = data.encaissements - attendus
    ecart_pct = (abs(ecart) / data.ca * 100) if data.ca else 0.0
    atypique = ecart_pct > data.seuil_pct
    return {
        "encaissements_attendus": round(attendus, 2),
        "ecart": round(ecart, 2),
        "ecart_pct": round(ecart_pct, 3),
        "atypique": atypique,
        "orientation": (
            "Écart supérieur au seuil : investiguer les transactions atypiques."
            if atypique else "Écart dans le seuil : pas d'investigation complémentaire requise."
        ),
    }


@app.post("/api/demo", status_code=201)
def request_demo(data: DemoRequest):
    if not re.fullmatch(EMAIL_RE, data.email):
        raise HTTPException(status_code=422, detail="Adresse e-mail invalide.")
    db.insert_demo(data.model_dump())
    return {"ok": True, "message": "Merci, nous vous recontactons sous 48 h."}


# ---------------------------------------------------------------- authentification
def public_user(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "firm": row["firm"]}


def current_user(authorization: str = Header(default="")):
    token = authorization.removeprefix("Bearer ").strip()
    try:
        user_id = decode_token(token)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Session expirée. Reconnectez-vous.")
    row = db.get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=401, detail="Compte introuvable.")
    return row


@app.post("/api/auth/register", status_code=201)
def register(data: RegisterInput):
    email = data.email.strip().lower()
    if not re.fullmatch(EMAIL_RE, email):
        raise HTTPException(status_code=422, detail="Adresse e-mail invalide.")
    row = db.create_user(email, data.name.strip(), data.firm.strip(), hash_password(data.password))
    return {"token": create_token(row["id"]), "user": public_user(row)}


@app.post("/api/auth/login")
def login(data: LoginInput):
    row = db.get_user_by_email(data.email.strip().lower())
    if not row or not verify_password(data.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect.")
    return {"token": create_token(row["id"]), "user": public_user(row)}


@app.get("/api/auth/me")
def me(user=Depends(current_user)):
    return public_user(user)
