"""Module 1 — administration du cabinet : édition cabinet, bureaux, garde-fou ADMIN."""
from __future__ import annotations

from _helpers_ecrans import ck

from app.core.security import hash_password
from app.models.cabinet import Bureau, Cabinet
from app.models.user import User


def test_administration_admin_edite_cabinet_et_bureaux(client, db_session):
    page = client.get("/vue/administration", cookies=ck(client))
    assert page.status_code == 200 and "Administration du cabinet" in page.text

    # Édition du cabinet (devise normalisée en majuscules).
    client.post("/vue/administration/cabinet",
                data={"nom": "Cabinet X", "pays": "France", "devise_defaut": "eur",
                      "referentiel_defaut": "PCG_FR"}, cookies=ck(client), follow_redirects=False)
    cab = db_session.query(Cabinet).first()
    assert cab.nom == "Cabinet X" and cab.devise_defaut == "EUR"

    # Ajout d'un bureau puis suppression.
    client.post("/vue/administration/bureau",
                data={"nom": "Bureau Lyon", "ville": "Lyon", "pays": "France"},
                cookies=ck(client), follow_redirects=False)
    b = db_session.query(Bureau).filter_by(nom="Bureau Lyon").first()
    assert b is not None and b.cabinet_id == cab.id
    client.post(f"/vue/administration/bureau/{b.id}/delete", cookies=ck(client), follow_redirects=False)
    assert db_session.query(Bureau).filter_by(nom="Bureau Lyon").first() is None


def test_administration_reservee_admin(client, db_session):
    cab = db_session.query(Cabinet).first()
    db_session.add(User(email="collab@test.io", hashed_password=hash_password("Pass!2026"),
                        nom_complet="Collab", is_active=True, cabinet_id=cab.id))
    db_session.commit()
    ck_collab = client.post("/login", data={"email": "collab@test.io", "password": "Pass!2026"},
                            follow_redirects=False).cookies
    r = client.get("/vue/administration", cookies=ck_collab)
    assert r.status_code == 403
