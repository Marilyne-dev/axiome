"""Phase 5 — extraction de texte / OCR des pièces (réel : Tesseract + pypdf)."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.models.audit import Document
from app.services import ocr_service


def test_extraction_csv_et_non_supporte(tmp_path):
    csv = tmp_path / "b.csv"; csv.write_text("compte;libelle\n512;Banque\n")
    r = ocr_service.extraire(csv, ".csv")
    assert r["statut"] == "ok" and "Banque" in r["texte"]
    exe = tmp_path / "x.bin"; exe.write_bytes(b"\x00\x01")
    assert ocr_service.extraire(exe, ".bin")["statut"] == "non_supporte"


def test_ocr_image_si_moteur_present(tmp_path):
    if not ocr_service.moteur_ocr_disponible():
        return  # environnement sans Tesseract : test neutre
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (440, 90), "white")
    ImageDraw.Draw(img).text((10, 30), "AXIOME AUDIT", fill="black")
    p = tmp_path / "img.png"; img.save(p)
    r = ocr_service.extraire(p, ".png")
    # Le moteur doit s'exécuter et renvoyer du texte. On ne vérifie pas la
    # reconnaissance exacte : l'OCR d'une image rendue en police bitmap par défaut
    # n'est pas un invariant fiable (ex. « AXIOME » parfois lu « AXOME »).
    assert r["statut"] == "ok"
    assert r["texte"].strip() != "" and "AUDIT" in r["texte"].upper()


def test_ocr_web_et_recherche(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    client.post(f"/missions/{mid}/vue/documents/upload", cookies=c,
                files={"fichier": ("note.txt", "tresorerie compte 512".encode(), "text/plain")},
                follow_redirects=False)
    doc = db_session.query(Document).filter_by(mission_id=mid).first()
    client.post(f"/missions/{mid}/vue/documents/{doc.id}/ocr", cookies=c, follow_redirects=False)
    db_session.expire_all()
    assert db_session.get(Document, doc.id).ocr_statut == "ok"
    r = client.get(f"/missions/{mid}/vue/documents?q=tresorerie", cookies=c)
    assert r.status_code == 200 and "note.txt" in r.text
