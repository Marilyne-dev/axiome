"""Fixtures de test : base SQLite en mémoire, données de référence, client HTTP."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # enregistre les tables  # noqa: F401
from app.api.scope import garde_cycle, garde_mission
from app.core.database import get_db
from app.core.security import hash_password
from app.db.init_db import _seed_devises, _seed_rbac, _seed_referentiels
from app.main import app
from app.models.base import Base
from app.models.cabinet import Cabinet
from app.models.user import Role, User


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = TestingSession()
    # Données de référence minimales
    _seed_referentiels(db)
    _seed_devises(db)
    _seed_rbac(db)
    # Un cabinet + un utilisateur admin de test (rattaché au cabinet)
    cabinet = Cabinet(nom="Cabinet Test", pays="France")
    db.add(cabinet); db.flush()
    admin_role = db.query(Role).filter_by(code="ADMIN").first()
    u = User(email="admin@axiome.io", hashed_password=hash_password("Test!2026"),
             nom_complet="Admin Test", is_active=True, cabinet_id=cabinet.id)
    u.roles.append(admin_role)
    db.add(u)
    db.commit()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()            # libère les connexions (évite les ResourceWarning en suite complète)


def pytest_configure(config):
    config.addinivalue_line("markers", "cloisonnement: garde la vraie vérification d'appartenance au cabinet")


@pytest.fixture()
def client(db_session, request):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    if "cloisonnement" not in request.keywords:
        # Les tests historiques créent leurs missions dans un cabinet distinct de l'admin de test :
        # ils vérifient la logique métier, pas le cloisonnement (couvert par les tests marqués).
        app.dependency_overrides[garde_mission] = lambda: None
        app.dependency_overrides[garde_cycle] = lambda: None
    with TestClient(app) as c:          # ferme le client httpx (évite les ResourceWarning)
        yield c
    app.dependency_overrides.clear()
