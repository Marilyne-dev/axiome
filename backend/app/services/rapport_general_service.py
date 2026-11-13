"""Rapport général signé : la nature de l'opinion est choisie par le signataire (NEP 700).

Aucune opinion n'est décidée par l'application. En version finale, l'opinion, son motif
(si réserve ou refus) et les points clés de l'audit sont obligatoires.
"""
from __future__ import annotations

from datetime import date

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.models.mission import Mission
from app.services.rapports_service import _entete, _finaliser, _sous_titre

OPINIONS = {
    "sans_reserve": "Certification sans réserve",
    "avec_reserves": "Certification avec réserve(s)",
    "refus": "Refus de certifier",
}

_OBJET = (
    "les comptes annuels sont, au regard du référentiel comptable applicable, réguliers et "
    "sincères et donnent une image fidèle du résultat des opérations de l'exercice écoulé ainsi "
    "que de la situation financière et du patrimoine de l'entité à la clôture de cet exercice."
)


def points_cles_suggeres(data: dict) -> list[str]:
    """Points clés préremplis depuis la synthèse (data = synthese_service.collecter)."""
    pts: list[str] = []
    for ligne in data.get("recap", []):
        if ligne.get("anomalie"):
            concl = (ligne.get("conclusion") or "anomalie relevée").strip()
            pts.append(f"Cycle {ligne['libelle']} : {concl}")
    if data.get("risques_eleves"):
        pts.append(f"{data['risques_eleves']} risque(s) élevé(s) ou critique(s) identifié(s) en planification.")
    if data.get("ci_deficients"):
        pts.append(f"{data['ci_deficients']} contrôle(s) interne(s) jugé(s) déficient(s).")
    if data.get("nb_variations_significatives"):
        pts.append(
            f"{data['nb_variations_significatives']} variation(s) N/N-1 supérieure(s) "
            "au seuil de signification, analysée(s) en revue analytique.")
    return pts


def erreurs_version_finale(opinion: str | None, motif: str, points: list[str]) -> list[str]:
    err: list[str] = []
    if opinion not in OPINIONS:
        err.append("Choisir la nature de l'opinion.")
    elif opinion != "sans_reserve" and not motif.strip():
        err.append("Le motif est obligatoire pour une réserve ou un refus de certifier.")
    if not [p for p in points if p.strip()]:
        err.append("Renseigner au moins un point clé de l'audit (justification des appréciations).")
    return err


def _phrase_opinion(opinion: str | None) -> str:
    if opinion == "sans_reserve":
        return "Nous certifions que " + _OBJET
    if opinion == "avec_reserves":
        return ("Sous la ou les réserves exposées dans la section « Fondement de l'opinion », "
                "nous certifions que " + _OBJET)
    if opinion == "refus":
        return ("En raison de l'importance des éléments décrits dans la section « Fondement de "
                "l'opinion », nous ne sommes pas en mesure de certifier que " + _OBJET)
    return "[À COMPLÉTER — nature de l'opinion à choisir par le signataire.]"


def rapport_general_signe(mission: Mission, *, opinion: str | None, motif: str,
                          points_cles: list[str], finale: bool,
                          signataire: str | None = None) -> bytes:
    doc = Document()
    if not finale:
        ban = doc.add_paragraph()
        r = ban.add_run("PROJET — NON FINALISÉ : ne pas diffuser")
        r.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(0xB0, 0x00, 0x20)
    _entete(doc, mission, "Rapport du commissaire aux comptes sur les comptes annuels")

    _sous_titre(doc, "Opinion")
    doc.add_paragraph(
        "En exécution de la mission qui nous a été confiée par votre assemblée générale, nous "
        "avons effectué l'audit des comptes annuels relatifs à l'exercice clos, tels qu'ils sont "
        "joints au présent rapport.")
    doc.add_paragraph(_phrase_opinion(opinion))

    _sous_titre(doc, "Fondement de l'opinion")
    doc.add_paragraph(
        "Nous avons effectué notre audit selon les normes d'exercice professionnel applicables en "
        "France. Nous estimons que les éléments que nous avons collectés sont suffisants et "
        "appropriés pour fonder notre opinion.")
    if opinion in ("avec_reserves", "refus"):
        lib = "Motif de la réserve" if opinion == "avec_reserves" else "Motif du refus de certifier"
        p = doc.add_paragraph()
        p.add_run(f"{lib} : ").bold = True
        p.add_run(motif.strip() or "[À COMPLÉTER]")

    _sous_titre(doc, "Justification des appréciations")
    pts = [x.strip() for x in points_cles if x.strip()]
    if pts:
        for x in pts:
            doc.add_paragraph(x, style="List Bullet")
    else:
        doc.add_paragraph("[À COMPLÉTER — points clés de l'audit et appréciations portées.]")

    _sous_titre(doc, "Vérifications spécifiques")
    doc.add_paragraph(
        "Nous avons également procédé, conformément aux normes d'exercice professionnel "
        "applicables, aux vérifications spécifiques prévues par les textes légaux et réglementaires.")

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    nom = f"\n{signataire}" if (finale and signataire) else ""
    p.add_run(f"Fait le {date.today():%d/%m/%Y}\nLe commissaire aux comptes{nom}").bold = True
    return _finaliser(doc)