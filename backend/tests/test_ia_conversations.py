"""Assistant IA : conversations enregistrées, historique renvoyé à l'IA, isolation par utilisateur."""
from __future__ import annotations

import app.api.routes_ia as routes
from app.core.security import hash_password
from app.models.user import User


def _entetes(client, email="admin@axiome.io"):
    t = client.post("/auth/login", json={"email": email, "password": "Test!2026"}).json()["access_token"]
    return {"Authorization": f"Bearer {t}"}


def test_creer_lister_lire_supprimer(client):
    h = _entetes(client)
    cid = client.post("/ia/conversations", headers=h).json()["id"]
    assert [c["id"] for c in client.get("/ia/conversations", headers=h).json()] == [cid]
    assert client.get(f"/ia/conversations/{cid}", headers=h).json()["messages"] == []
    assert client.delete(f"/ia/conversations/{cid}", headers=h).json() == {"ok": True}
    assert client.get("/ia/conversations", headers=h).json() == []


def test_message_sans_cle_refuse(client):
    h = _entetes(client)
    cid = client.post("/ia/conversations", headers=h).json()["id"]
    r = client.post(f"/ia/conversations/{cid}/messages", headers=h, json={"contenu": "Bonjour"})
    assert r.status_code == 503


def test_historique_envoye_et_enregistre(client, monkeypatch):
    monkeypatch.setattr(routes, "ia_disponible", lambda: True)
    appels = []

    def faux(historique, contexte=""):
        appels.append([dict(m) for m in historique])
        return {"disponible": True, "reponse": f"Réponse {len(historique)}", "avertissement": "à valider"}

    monkeypatch.setattr(routes, "converser", faux)
    h = _entetes(client)
    cid = client.post("/ia/conversations", headers=h).json()["id"]
    r1 = client.post(f"/ia/conversations/{cid}/messages", headers=h, json={"contenu": "Bonjour"})
    assert r1.status_code == 200
    r2 = client.post(f"/ia/conversations/{cid}/messages", headers=h, json={"contenu": "Et ensuite ?"})
    assert r2.status_code == 200
    # Le 2e appel contient toute la conversation : question, réponse, nouvelle question.
    assert [m["role"] for m in appels[1]] == ["user", "assistant", "user"]
    conv = client.get(f"/ia/conversations/{cid}", headers=h).json()
    assert [m["role"] for m in conv["messages"]] == ["user", "assistant", "user", "assistant"]
    assert conv["titre"] == "Bonjour"


def test_echec_ia_n_enregistre_rien(client, monkeypatch):
    monkeypatch.setattr(routes, "ia_disponible", lambda: True)
    monkeypatch.setattr(routes, "converser", lambda h, c="": {"disponible": True, "erreur": "boom", "reponse": ""})
    h = _entetes(client)
    cid = client.post("/ia/conversations", headers=h).json()["id"]
    r = client.post(f"/ia/conversations/{cid}/messages", headers=h, json={"contenu": "Test"})
    assert r.status_code == 502
    assert client.get(f"/ia/conversations/{cid}", headers=h).json()["messages"] == []


def test_conversation_d_un_autre_utilisateur_introuvable(client, db_session):
    h = _entetes(client)
    cid = client.post("/ia/conversations", headers=h).json()["id"]
    db_session.add(User(email="autre@axiome.io", hashed_password=hash_password("Test!2026"),
                        nom_complet="Autre", is_active=True))
    db_session.commit()
    h2 = _entetes(client, "autre@axiome.io")
    assert client.get(f"/ia/conversations/{cid}", headers=h2).status_code == 404
    assert client.delete(f"/ia/conversations/{cid}", headers=h2).status_code == 404
    assert client.get("/ia/conversations", headers=h2).json() == []
