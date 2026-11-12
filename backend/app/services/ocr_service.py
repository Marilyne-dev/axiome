"""Extraction de texte / OCR des pièces de la GED.

Réel et fonctionnel selon le format :
- .txt/.csv           : lecture directe ;
- .docx               : python-docx (paragraphes) ;
- .xlsx/.xls          : openpyxl (valeurs de cellules) ;
- .pdf                : couche texte (pypdf) ; si absente, rastérisation (poppler)
                        puis OCR (Tesseract) page par page ;
- .png/.jpg/.jpeg     : OCR (Tesseract).

La disponibilité de l'OCR image dépend du binaire Tesseract ; en son absence, les
formats texte/pdf-texte restent extraits, et les images renvoient un statut clair.
"""
from __future__ import annotations

import shutil
from pathlib import Path

# Détection paresseuse des dépendances optionnelles.
try:
    import pytesseract
    from PIL import Image
    _TESSERACT = shutil.which("tesseract") is not None
except Exception:  # noqa: BLE001
    _TESSERACT = False

try:
    import pdf2image
    _POPPLER = shutil.which("pdftoppm") is not None
except Exception:  # noqa: BLE001
    _POPPLER = False

_IMAGES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
_MAX_CARS = 200_000  # borne de sécurité sur le texte stocké


def moteur_ocr_disponible() -> bool:
    return _TESSERACT


def _langue() -> str:
    """'fra' si le pack est installé, sinon 'eng'."""
    if not _TESSERACT:
        return "eng"
    try:
        langs = pytesseract.get_languages(config="")
        return "fra" if "fra" in langs else "eng"
    except Exception:  # noqa: BLE001
        return "eng"


def _ocr_image(chemin: Path) -> str:
    return pytesseract.image_to_string(Image.open(chemin), lang=_langue())


def _texte_pdf(chemin: Path) -> tuple[str, str]:
    """Retourne (texte, méthode). Essaie la couche texte, sinon OCR par rastérisation."""
    from pypdf import PdfReader
    reader = PdfReader(str(chemin))
    texte = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if texte:
        return texte, "pdf_texte"
    if _TESSERACT and _POPPLER:
        pages = pdf2image.convert_from_path(str(chemin), dpi=200)
        ocr = "\n".join(pytesseract.image_to_string(img, lang=_langue()) for img in pages).strip()
        return ocr, "pdf_ocr"
    return "", "pdf_sans_texte"


def _texte_docx(chemin: Path) -> str:
    import docx
    return "\n".join(p.text for p in docx.Document(str(chemin)).paragraphs)


def _texte_xlsx(chemin: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(str(chemin), read_only=True, data_only=True)
    morceaux = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            morceaux.append(" ".join("" if c is None else str(c) for c in row))
    wb.close()
    return "\n".join(morceaux)


def extraire(chemin: Path, extension: str) -> dict:
    """Extrait le texte d'une pièce. Retourne {statut, methode, texte}.

    statut : ok | vide | indisponible | non_supporte | erreur
    """
    ext = extension.lower()
    if not ext.startswith("."):
        ext = "." + ext
    if not chemin.exists():
        return {"statut": "erreur", "methode": "", "texte": "Fichier absent du stockage."}
    try:
        if ext in {".txt", ".csv", ".xml"}:
            texte, methode = chemin.read_text(encoding="utf-8", errors="replace"), "lecture"
        elif ext == ".docx":
            texte, methode = _texte_docx(chemin), "docx"
        elif ext in {".xlsx", ".xls"}:
            texte, methode = _texte_xlsx(chemin), "xlsx"
        elif ext == ".pdf":
            texte, methode = _texte_pdf(chemin)
        elif ext in _IMAGES:
            if not _TESSERACT:
                return {"statut": "indisponible", "methode": "ocr",
                        "texte": "OCR indisponible : moteur Tesseract non installé."}
            texte, methode = _ocr_image(chemin), "ocr"
        else:
            return {"statut": "non_supporte", "methode": "", "texte": ""}
    except Exception as exc:  # noqa: BLE001 — on remonte l'échec sans planter la GED
        return {"statut": "erreur", "methode": "", "texte": f"Échec d'extraction : {exc}"}

    texte = (texte or "").strip()[:_MAX_CARS]
    return {"statut": "ok" if texte else "vide", "methode": methode, "texte": texte}
