"""Phase 5 — GED : upload sécurisé, téléchargement, suppression."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.audit import Document


def test_upload_download_delete(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    # upload d'une pièce texte
    r = client.post(f"/missions/{mid}/vue/documents/upload", cookies=c,
                    files={"fichier": ("note.txt", b"bonjour", "text/plain")},
                    data={"cycle_code": "TRESORERIE"}, follow_redirects=False)
    assert r.status_code == 302
    doc = db_session.query(Document).filter_by(mission_id=mid).first()
    assert doc is not None and doc.taille == 7 and doc.cycle_code == "TRESORERIE"
    # téléchargement -> contenu restitué
    d = client.get(f"/missions/{mid}/vue/documents/{doc.id}/download", cookies=c)
    assert d.status_code == 200 and d.content == b"bonjour"
    # suppression
    client.post(f"/missions/{mid}/vue/documents/{doc.id}/delete", cookies=c, follow_redirects=False)
    assert db_session.query(Document).filter_by(mission_id=mid).count() == 0


def test_upload_extension_refusee(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    r = client.post(f"/missions/{mid}/vue/documents/upload", cookies=c,
                    files={"fichier": ("malware.exe", b"MZ", "application/octet-stream")},
                    follow_redirects=False)
    assert r.status_code == 302 and "err=" in r.headers["location"]
    assert db_session.query(Document).filter_by(mission_id=mid).count() == 0
