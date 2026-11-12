"""Module 17 — Génération des rapports Word/PDF.

Trois livrables conformes à la démarche NEP :
- Lettre de mission (NEP 210) ;
- Rapport général de certification des comptes (NEP 700) ;
- Note de synthèse de la mission (revue analytique NEP 520 + conclusions).

Le contenu est un SQUELETTE professionnel pré-rempli à partir des données de la
mission ; le commissaire aux comptes complète et engage sa signature. Aucune
opinion n'est arrêtée automatiquement.
"""
from __future__ import annotations

import io
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.models.mission import Mission

_NAVY = RGBColor(0x0B, 0x25, 0x45)
_GOLD = RGBColor(0xC9, 0xA2, 0x27)


def _titre(doc: Document, texte: str, taille: int = 16) -> None:
    p = doc.add_paragraph()
    r = p.add_run(texte)
    r.bold = True
    r.font.size = Pt(taille)
    r.font.color.rgb = _NAVY


def _sous_titre(doc: Document, texte: str) -> None:
    p = doc.add_paragraph()
    r = p.add_run(texte)
    r.bold = True
    r.font.size = Pt(12)
    r.font.color.rgb = _NAVY
    p.space_before = Pt(10)


def _entete(doc: Document, mission: Mission, sous_titre: str) -> None:
    """Bandeau de tête : cabinet, client, référentiel."""
    band = doc.add_paragraph()
    b = band.add_run("AXIOME — Commissariat aux comptes")
    b.bold = True
    b.font.color.rgb = _GOLD
    b.font.size = Pt(10)
    _titre(doc, sous_titre, 18)
    client = mission.client.raison_sociale if mission.client else "—"
    meta = doc.add_paragraph()
    meta.add_run(f"Entité : {client}\n").bold = True
    meta.add_run(
        f"Mission : {mission.intitule}\n"
        f"Référentiel : {mission.referentiel}   ·   Pays : {mission.pays}   ·   Devise : {mission.devise}\n"
        f"Date d'édition : {date.today():%d/%m/%Y}"
    )
    doc.add_paragraph("_" * 70)


def _finaliser(doc: Document) -> bytes:
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def lettre_mission(mission: Mission) -> bytes:
    """Lettre de mission (NEP 210)."""
    doc = Document()
    _entete(doc, mission, "Lettre de mission")
    client = mission.client.raison_sociale if mission.client else "l'entité"
    doc.add_paragraph(
        f"Madame, Monsieur les dirigeants de {client},\n\n"
        "Nous vous remercions de la confiance que vous nous témoignez en nous confiant la mission "
        "de commissariat aux comptes de votre entité. La présente lettre a pour objet de définir "
        "les termes et conditions de notre mission, conformément à la norme d'exercice professionnel NEP 210."
    )
    _sous_titre(doc, "1. Objet et étendue de la mission")
    doc.add_paragraph(
        "Notre mission consiste à certifier que les comptes annuels sont réguliers et sincères et "
        "donnent une image fidèle du résultat des opérations de l'exercice écoulé ainsi que de la "
        "situation financière et du patrimoine de l'entité à la clôture, dans le respect du référentiel "
        f"comptable applicable ({mission.referentiel})."
    )
    _sous_titre(doc, "2. Responsabilités respectives")
    doc.add_paragraph(
        "La direction est responsable de l'établissement des comptes et du contrôle interne. Il nous "
        "appartient de formuler une opinion sur ces comptes sur la base de notre audit, conduit selon "
        "les normes d'exercice professionnel applicables en France."
    )
    _sous_titre(doc, "3. Calendrier et honoraires")
    doc.add_paragraph(
        "Le calendrier d'intervention et le budget d'honoraires font l'objet d'une annexe distincte, "
        "déterminée en fonction de la nature et de l'étendue des diligences à mettre en œuvre."
    )
    doc.add_paragraph("\nFait pour accord,\n\nLe commissaire aux comptes\t\t\tLa direction")
    return _finaliser(doc)


def rapport_general(mission: Mission) -> bytes:
    """Rapport général de certification des comptes (NEP 700)."""
    doc = Document()
    _entete(doc, mission, "Rapport du commissaire aux comptes sur les comptes annuels")
    _sous_titre(doc, "Opinion")
    doc.add_paragraph(
        "En exécution de la mission qui nous a été confiée par votre assemblée générale, nous avons "
        "effectué l'audit des comptes annuels relatifs à l'exercice clos, tels qu'ils sont joints au "
        "présent rapport.\n\n"
        "[À COMPLÉTER — nature de l'opinion : certification sans réserve / avec réserve(s) / refus] : "
        "nous certifions que les comptes annuels sont, au regard du référentiel comptable applicable, "
        "réguliers et sincères et donnent une image fidèle du résultat des opérations de l'exercice "
        "écoulé ainsi que de la situation financière et du patrimoine de l'entité à la clôture."
    )
    _sous_titre(doc, "Fondement de l'opinion")
    doc.add_paragraph(
        "Nous avons effectué notre audit selon les normes d'exercice professionnel applicables en "
        "France. Nous estimons que les éléments que nous avons collectés sont suffisants et appropriés "
        "pour fonder notre opinion."
    )
    _sous_titre(doc, "Justification des appréciations")
    doc.add_paragraph("[À COMPLÉTER — points clés de l'audit et appréciations portées.]")
    _sous_titre(doc, "Vérifications spécifiques")
    doc.add_paragraph(
        "Nous avons également procédé, conformément aux normes d'exercice professionnel applicables, "
        "aux vérifications spécifiques prévues par les textes légaux et réglementaires."
    )
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"Fait le {date.today():%d/%m/%Y}\nLe commissaire aux comptes").bold = True
    return _finaliser(doc)


def note_synthese(mission: Mission, *, seuil: float | None = None,
                  conclusions: list[dict] | None = None) -> bytes:
    """Note de synthèse de la mission (revue analytique NEP 520 + conclusions par cycle)."""
    doc = Document()
    _entete(doc, mission, "Note de synthèse de la mission")
    _sous_titre(doc, "1. Seuil de signification")
    doc.add_paragraph(
        f"Le seuil de signification retenu pour la mission s'élève à "
        f"{('%s %s' % (format(seuil, ',.0f').replace(',', ' '), mission.devise)) if seuil else '[à déterminer]'}. "
        "Il a servi de référence à la planification et à l'appréciation des anomalies."
    )
    _sous_titre(doc, "2. Revue analytique (NEP 520)")
    doc.add_paragraph(
        "La revue analytique a consisté à comparer les données de l'exercice à celles de l'exercice "
        "précédent et à analyser les variations significatives au regard du seuil défini."
    )
    _sous_titre(doc, "3. Conclusions par cycle")
    table = doc.add_table(rows=1, cols=3)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    hdr[0].text, hdr[1].text, hdr[2].text = "Cycle", "Conclusion", "Anomalie ?"
    for c in (conclusions or []):
        row = table.add_row().cells
        row[0].text = str(c.get("cycle", ""))
        row[1].text = str(c.get("conclusion", "—"))
        row[2].text = "Oui" if c.get("anomalie") else "Non"
    if not conclusions:
        row = table.add_row().cells
        row[0].text = "[à compléter]"; row[1].text = "—"; row[2].text = "—"
    _sous_titre(doc, "4. Opinion proposée")
    doc.add_paragraph(
        "[À COMPLÉTER par l'associé signataire — synthèse des travaux et orientation de l'opinion.]"
    )
    return _finaliser(doc)


def _montant(v: float, devise: str) -> str:
    return f"{format(v or 0, ',.0f').replace(',', ' ')} {devise}"


def feuille_garde(mission: Mission, data: dict, edite_par: str | None = None) -> bytes:
    """Feuille de garde imprimable du dossier : identité, seuils, points d'attention, récap.

    `data` provient de `synthese_service.collecter()` (source unique de vérité).
    `edite_par` (optionnel) appose un cachet d'édition en pied de document.
    """
    devise = mission.devise or ""
    doc = Document()
    _entete(doc, mission, "Feuille de garde — Synthèse du dossier")

    _sous_titre(doc, "1. Seuils retenus")
    seuils = data.get("seuils")
    if seuils and seuils.seuil_signification:
        p = doc.add_paragraph()
        p.add_run(f"Signification : {_montant(seuils.seuil_signification, devise)}\n")
        p.add_run(f"Planification : {_montant(seuils.seuil_planification, devise)}\n")
        p.add_run(f"Remontée : {_montant(seuils.seuil_remontee, devise)}\n")
        p.add_run(f"Base retenue : {seuils.base_retenue or '—'}")
    else:
        doc.add_paragraph("Seuils non renseignés — à saisir dans l'écran « Seuils » de la mission.")

    _sous_titre(doc, "2. Points d'attention")
    doc.add_paragraph(
        f"Cycles en anomalie : {data['cycles_anomalie']}   ·   "
        f"Risques élevés/critiques : {data['risques_eleves']}   ·   "
        f"Contrôles internes déficients : {data['ci_deficients']}   ·   "
        f"Contrôles automatiques en échec : {data.get('controles_anomalies', 0)}   ·   "
        f"Variations significatives (> seuil) : {data.get('nb_variations_significatives', 0)}"
    )
    benford = data.get("benford") or {}
    if benford.get("exploitable"):
        doc.add_paragraph(
            f"Loi de Benford (soldes N) : {benford['conformite']} "
            f"(MAD {benford['mad']}, n={benford['n']}) — indicateur analytique, non probant."
        )
    ff = data.get("fraude_fec")
    if ff is not None:
        wd = f"{ff.window_part * 100:.1f}%" if ff.window_applicable else "n/a"
        doc.add_paragraph(
            f"Analyse fraude FEC (NEP 240) : structuration {ff.structuration_nb} · "
            f"window dressing {wd}{' (suspicion)' if ff.window_suspicion else ''} · "
            f"nombres ronds {ff.nombres_ronds_nb} · doublons {ff.doublons_nb} · "
            f"contrepassations {ff.contrepassations_nb} — signaux non probants."
        )
        if ff.tva_applicable:
            doc.add_paragraph(
                f"Cohérence TVA : taux collecté implicite {ff.tva_taux_implicite * 100:.1f}%"
                f"{' — à justifier' if not ff.tva_plausible else ' (dans la bande plausible)'}."
            )
        if ff.tiers_fournisseurs_nb:
            doc.add_paragraph(
                f"Tiers fournisseurs : {ff.tiers_fournisseurs_nb} auxiliaires · "
                f"concentration 1er {ff.tiers_top_part * 100:.1f}% · "
                f"montants exclusivement ronds {ff.tiers_ronds_nb} · "
                f"écriture unique élevée {ff.tiers_uniques_eleves_nb} — signaux non probants."
            )
        from app.services.fraude_fec_service import signaux_orm
        nb_sig, libelles = signaux_orm(ff)
        doc.add_paragraph(
            f"Vigilance fraude (NEP 240) : {nb_sig} signal(aux) déclenché(s)"
            f"{' — ' + ', '.join(libelles) if libelles else ''}. "
            "Indicateur agrégé, requiert le jugement de l'auditeur."
        )

    _sous_titre(doc, "3. Récapitulatif par cycle")
    table = doc.add_table(rows=1, cols=6)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, titre in enumerate(("Cycle", "Nb comptes", "Total Solde N", "Total Solde N-1",
                               "Anomalie", "Conclusion")):
        hdr[i].text = titre
    for ligne in data.get("recap", []):
        row = table.add_row().cells
        row[0].text = ligne["libelle"]
        row[1].text = str(ligne["nb"])
        row[2].text = _montant(ligne["total_n"], devise)
        row[3].text = _montant(ligne["total_n1"], devise)
        row[4].text = "Oui" if ligne["anomalie"] else "—"
        row[5].text = ligne["conclusion"][:120] or "—"
    if not data.get("recap"):
        row = table.add_row().cells
        row[0].text = "Aucune ligne de balance importée."

    doc.add_paragraph(
        "\nCette feuille de garde synthétise l'état du dossier ; l'appréciation finale et "
        "l'opinion relèvent du jugement de l'associé signataire."
    )
    if edite_par:
        cachet = doc.add_paragraph()
        run = cachet.add_run(f"Édité le {date.today():%d/%m/%Y} par {edite_par}.")
        run.italic = True
        run.font.size = Pt(9)
    return _finaliser(doc)


def rapport_assurance_csrd(mission: Mission, etat: dict) -> bytes:
    """Rapport d'assurance (limitée) sur les informations de durabilité (CSRD/ESRS).

    Livrable de travail produit à partir de l'analyse de double matérialité et de la
    couverture des points de données ESRS. Aucune assurance n'est arrêtée
    automatiquement : le commissaire aux comptes complète et engage sa signature.
    """
    doc = Document()
    _entete(doc, mission, "Rapport d'assurance sur les informations de durabilité")

    _sous_titre(doc, "Objet et étendue")
    doc.add_paragraph(
        "Le présent rapport porte sur les informations de durabilité établies en application "
        "de la directive CSRD et des normes ESRS, dans le cadre d'une mission d'assurance "
        "limitée. ESRS 1 (exigences générales) et ESRS 2 (informations générales) s'appliquent "
        "en toute hypothèse ; les thèmes topiques sont retenus selon l'analyse de double "
        "matérialité (matérialité d'impact et matérialité financière)."
    )

    _sous_titre(doc, "Analyse de double matérialité")
    table = doc.add_table(rows=1, cols=4)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Thème ESRS", "Matérialité d'impact", "Matérialité financière", "Retenu"]):
        hdr[i].paragraphs[0].add_run(h).bold = True
    ech = etat["echelle"]
    for t in etat["themes"]:
        row = table.add_row().cells
        row[0].text = f"{t['code']} · {t['libelle']}"
        row[1].text = f"{t['impact']} — {ech.get(t['impact'], '')}"
        row[2].text = f"{t['financier']} — {ech.get(t['financier'], '')}"
        row[3].text = "Oui" if t["retenu"] else "Non"

    _sous_titre(doc, "Thèmes retenus et couverture des points de données")
    if etat["retenus"]:
        for t in etat["retenus"]:
            doc.add_paragraph().add_run(f"{t['code']} · {t['libelle']}").bold = True
            for p in etat["points_par_theme"].get(t["code"], []):
                marque = "[X]" if p.couvert else "[ ]"
                doc.add_paragraph(f"{marque} {p.code} — {p.libelle}")
    else:
        doc.add_paragraph("Aucun thème retenu : analyse de matérialité à réaliser.")

    _sous_titre(doc, "Conclusion (assurance limitée)")
    doc.add_paragraph(
        f"Thèmes retenus : {etat['nb_retenus']}/10. "
        f"Couverture des points de données : {etat['couverts']}/{etat['total_points']} "
        f"({etat['couverture_pct']} %). {etat['conclusion']}"
    )
    doc.add_paragraph(
        "Sur la base de nos travaux, et sauf éléments relevés ci-dessus, nous n'avons pas relevé "
        "d'anomalie significative de nature à remettre en cause la conformité des informations de "
        "durabilité au référentiel ESRS. [Projet — à finaliser et signer par le commissaire aux comptes.]"
    )
    note = doc.add_paragraph()
    r = note.add_run(
        "Le module met en œuvre un sous-ensemble représentatif des points de données ESRS et une "
        "méthodologie de travail non certifiante ; la liste exhaustive et les automatisations "
        "avancées restent à approfondir."
    )
    r.italic = True
    r.font.size = Pt(8)
    return _finaliser(doc)



def note_verifications_specifiques(mission: Mission, etat: dict) -> bytes:
    """Note de vérifications spécifiques (art. L.823-10) : concordance et points de contrôle.

    Livrable de travail produit à partir du contrôle de concordance du rapport de gestion
    et des points de vérification. Le commissaire aux comptes conclut et engage sa signature.
    """
    dev = mission.devise or "EUR"
    doc = Document()
    _entete(doc, mission, "Note de vérifications spécifiques")

    _sous_titre(doc, "Objet et cadre")
    doc.add_paragraph(
        "En application de l'article L.823-10 du Code de commerce, le commissaire aux comptes "
        "vérifie la concordance avec les comptes annuels des informations financières données dans "
        "le rapport de gestion et procède aux vérifications spécifiques prévues par la loi. Les "
        "montants « issus des comptes » sont établis à partir de la balance ; ils sont indicatifs "
        "et validés par le commissaire aux comptes."
    )

    _sous_titre(doc, "Contrôle de concordance du rapport de gestion")
    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, h in enumerate(["Rubrique", "Montant issu des comptes",
                           "Montant au rapport de gestion", "Écart", "Statut"]):
        hdr[i].paragraphs[0].add_run(h).bold = True
    libelle_statut = {"concordant": "Concordant", "ecart": "Écart", "non_renseigne": "Non renseigné"}
    for lg in etat["lignes"]:
        row = table.add_row().cells
        row[0].text = lg["libelle"]
        row[1].text = _montant(lg["montant_comptes"], dev)
        row[2].text = _montant(lg["montant_rapport"], dev) if lg["montant_rapport"] is not None else "—"
        row[3].text = _montant(lg["ecart"], dev) if lg["ecart"] is not None else "—"
        row[4].text = libelle_statut.get(lg["statut"], lg["statut"])
    doc.add_paragraph(
        "Tolérance appliquée : 1 unité de devise ou 0,5 % du montant des comptes."
    ).runs[0].italic = True

    _sous_titre(doc, "Points de vérification spécifique")
    for p in etat["points"]:
        marque = "[X]" if p["fait"] else "[ ]"
        txt = f"{marque} {p['libelle']}"
        if p["observation"]:
            txt += f" — {p['observation']}"
        doc.add_paragraph(txt)

    _sous_titre(doc, "Conclusion")
    doc.add_paragraph(
        f"Montants renseignés : {etat['renseignes']}/{etat['nb_lignes']} · "
        f"concordants : {etat['concordants']} · écarts : {etat['ecarts']}. "
        f"Points contrôlés : {etat['points_faits']}/{etat['nb_points']}. {etat['conclusion']}"
    )
    doc.add_paragraph(
        "Sous réserve des écarts éventuels relevés ci-dessus et de leur justification, nous n'avons "
        "pas d'observation à formuler sur la concordance des informations du rapport de gestion avec "
        "les comptes annuels. [Projet — à finaliser et signer par le commissaire aux comptes.]"
    )
    return _finaliser(doc)



def rapport_commissaire_fusion(mission: Mission, etat: dict) -> bytes:
    """Rapport du commissaire à la fusion : parité d'échange et valeur des apports.

    Livrable de travail produit à partir du contrôle de parité. Le commissaire à la fusion
    conclut sur le caractère équitable du rapport d'échange et engage sa signature.
    """
    dev = mission.devise or "EUR"
    d = etat["dossier"]
    doc = Document()
    _entete(doc, mission, "Rapport du commissaire à la fusion")

    _sous_titre(doc, "Objet")
    doc.add_paragraph(
        "En application des articles L.236-10 et suivants du Code de commerce, nous présentons notre "
        "rapport sur les modalités de la fusion par absorption de "
        f"« {d.nom_absorbee} » (absorbée) par « {d.nom_absorbante} » (absorbante), portant sur le "
        "caractère équitable du rapport d'échange et sur la valeur des apports."
    )

    _sous_titre(doc, "Valeurs retenues et rapport d'échange")
    table = doc.add_table(rows=1, cols=2)
    table.style = "Light Grid Accent 1"
    table.rows[0].cells[0].paragraphs[0].add_run("Élément").bold = True
    table.rows[0].cells[1].paragraphs[0].add_run("Valeur").bold = True
    lignes = [
        (f"Valeur retenue — {d.nom_absorbante}", _montant(etat["valeur_a"], dev)),
        (f"Valeur retenue — {d.nom_absorbee}", _montant(etat["valeur_b"], dev)),
        ("Valeur unitaire — absorbante", f"{etat['vu_a']:.2f} {dev}"),
        ("Valeur unitaire — absorbée", f"{etat['vu_b']:.2f} {dev}"),
        ("Parité théorique (actions absorbante pour 1 action absorbée)", f"{etat['parite_theorique']:.4f}"),
        (f"Parité retenue au traité ({etat['parite_num']} pour {etat['parite_den']})", f"{etat['parite_retenue']:.4f}"),
        ("Écart parité retenue / théorique", f"{etat['ecart'] * 100:.1f} %" if etat["ecart"] is not None else "—"),
    ]
    for lib, val in lignes:
        r = table.add_row().cells
        r[0].text = lib
        r[1].text = val

    _sous_titre(doc, "Rémunération des apports")
    table2 = doc.add_table(rows=1, cols=2)
    table2.style = "Light Grid Accent 1"
    table2.rows[0].cells[0].paragraphs[0].add_run("Élément").bold = True
    table2.rows[0].cells[1].paragraphs[0].add_run("Montant").bold = True
    for lib, val in [
        ("Actions absorbante à créer", f"{etat['actions_creees']:,.0f}".replace(",", " ")),
        ("Augmentation de capital", _montant(etat["augmentation_capital"], dev)),
        ("Actif net apporté", _montant(etat["actif_net_apporte"], dev)),
        ("Prime de fusion", _montant(etat["prime_fusion"], dev)),
    ]:
        r = table2.add_row().cells
        r[0].text = lib
        r[1].text = val
    doc.add_paragraph(
        "Contrôle : l'actif net apporté est "
        + ("au moins égal" if etat["controle_apport"] else "INFÉRIEUR")
        + " à l'augmentation de capital."
    )

    if etat["alertes"]:
        _sous_titre(doc, "Points relevés")
        for a in etat["alertes"]:
            doc.add_paragraph(f"— {a}")

    _sous_titre(doc, "Conclusion")
    doc.add_paragraph(etat["conclusion"])
    doc.add_paragraph(
        "Sur la base de nos travaux, et sous réserve des points éventuellement relevés ci-dessus, le "
        "rapport d'échange proposé nous paraît équitable. [Projet — à finaliser et signer par le "
        "commissaire à la fusion.]"
    )
    note = doc.add_paragraph()
    run = note.add_run(
        "La valeur retenue par société est calculée comme la moyenne des méthodes saisies ; "
        "la pondération des approches relève du jugement du commissaire."
    )
    run.italic = True
    run.font.size = Pt(8)
    return _finaliser(doc)


def docx_vers_pdf(contenu_docx: bytes) -> bytes:
    """Convertit un .docx en .pdf via LibreOffice (rendu fidèle)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "rapport.docx"
        src.write_bytes(contenu_docx)
        subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", tmp, str(src)],
            check=True, capture_output=True, timeout=90,
        )
        return (Path(tmp) / "rapport.pdf").read_bytes()
