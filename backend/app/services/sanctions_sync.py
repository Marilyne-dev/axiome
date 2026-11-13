"""Mise à jour de la liste de sanctions depuis les sources OFFICIELLES (OFAC/SDN et ONU).

Produit `storage/sanctions/liste.csv` (nom,type,programme,source), que `sanctions_service` utilise
déjà en priorité sur la liste de démonstration. Lancement :

    python -m app.tools.maj_sanctions            # OFAC + ONU
    python -m app.tools.maj_sanctions --ofac     # une seule source

Garde-fous : la liste existante n'est remplacée que si TOUTES les sources demandées se téléchargent et
fournissent un volume plausible ; l'écriture est atomique. La liste de l'Union européenne n'est pas
incluse : son téléchargement exige un jeton personnel du portail FSF — voir `--csv-local`.
"""
from __future__ import annotations

import csv
import io
import json
import os
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

URL_OFAC_SDN = "https://www.treasury.gov/ofac/downloads/sdn.csv"
URL_OFAC_ALT = "https://www.treasury.gov/ofac/downloads/alt.csv"
URL_ONU = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
MIN_ENTREES = {"OFAC": 1000, "ONU": 200}  # en dessous : téléchargement tronqué probable


def _norm(nom: str) -> str:
    s = unicodedata.normalize("NFKD", nom or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _retourner_nom(nom: str) -> str:
    """OFAC écrit les personnes « NOM, Prénom » : on restitue « Prénom NOM »."""
    if "," in nom:
        a, b = nom.split(",", 1)
        return f"{b.strip()} {a.strip()}".strip()
    return nom.strip()


def _type_ofac(brut: str) -> str:
    b = (brut or "").strip().lower()
    if b == "individual":
        return "personne"
    if b in ("-0-", ""):
        return "entite"
    return b  # vessel, aircraft


def parse_ofac_sdn(texte_sdn: str, texte_alt: str = "") -> list[dict]:
    """sdn.csv : sans en-tête — [ent_num, SDN_Name, SDN_Type, Program, Title, …] ; alt.csv : [ent_num, alt_num, type, alt_name]."""
    base: dict[str, dict] = {}
    sorties: list[dict] = []
    for ligne in csv.reader(io.StringIO(texte_sdn)):
        if len(ligne) < 4 or not ligne[0].strip().isdigit():
            continue
        type_ = _type_ofac(ligne[2])
        nom = _retourner_nom(ligne[1]) if type_ == "personne" else ligne[1].strip()
        prog = "" if ligne[3].strip() == "-0-" else ligne[3].strip()
        base[ligne[0].strip()] = {"type": type_, "programme": prog}
        if nom:
            sorties.append({"nom": nom, "type": type_, "programme": prog, "source": "OFAC"})
    for ligne in csv.reader(io.StringIO(texte_alt)):
        if len(ligne) < 4 or ligne[0].strip() not in base:
            continue
        b = base[ligne[0].strip()]
        alias = _retourner_nom(ligne[3]) if b["type"] == "personne" else ligne[3].strip()
        if alias and alias != "-0-":
            sorties.append({"nom": alias, "type": b["type"], "programme": b["programme"], "source": "OFAC"})
    return sorties


def parse_onu_xml(texte: str) -> list[dict]:
    """Liste consolidée du Conseil de sécurité (INDIVIDUAL / ENTITY, avec alias)."""
    racine = ET.fromstring(texte)
    sorties: list[dict] = []

    def txt(el, tag):
        n = el.find(tag)
        return (n.text or "").strip() if n is not None and n.text else ""

    for ind in racine.iter("INDIVIDUAL"):
        prog = txt(ind, "UN_LIST_TYPE")
        nom = " ".join(p for p in (txt(ind, "FIRST_NAME"), txt(ind, "SECOND_NAME"),
                                   txt(ind, "THIRD_NAME"), txt(ind, "FOURTH_NAME")) if p)
        if nom:
            sorties.append({"nom": nom, "type": "personne", "programme": prog, "source": "ONU"})
        for al in ind.iter("INDIVIDUAL_ALIAS"):
            a = txt(al, "ALIAS_NAME")
            if a:
                sorties.append({"nom": a, "type": "personne", "programme": prog, "source": "ONU"})
    for ent in racine.iter("ENTITY"):
        prog = txt(ent, "UN_LIST_TYPE")
        nom = txt(ent, "FIRST_NAME")
        if nom:
            sorties.append({"nom": nom, "type": "entite", "programme": prog, "source": "ONU"})
        for al in ent.iter("ENTITY_ALIAS"):
            a = txt(al, "ALIAS_NAME")
            if a:
                sorties.append({"nom": a, "type": "entite", "programme": prog, "source": "ONU"})
    return sorties


def parse_csv_local(texte: str, source: str = "local") -> list[dict]:
    """CSV générique (ex. export UE téléchargé à la main) : colonnes nom[,type,programme]."""
    sorties = []
    for ligne in csv.DictReader(io.StringIO(texte)):
        nom = (ligne.get("nom") or "").strip()
        if nom:
            sorties.append({"nom": nom, "type": (ligne.get("type") or "").strip(),
                            "programme": (ligne.get("programme") or "").strip(), "source": source})
    return sorties


def dedoublonner(entrees: list[dict]) -> list[dict]:
    vus: set[tuple[str, str]] = set()
    uniques = []
    for e in entrees:
        cle = (_norm(e["nom"]), e["source"])
        if cle[0] and cle not in vus:
            vus.add(cle)
            uniques.append(e)
    return uniques


def ecrire_liste(entrees: list[dict], chemin: Path) -> int:
    """Écriture atomique de liste.csv + liste.meta.json. Retourne le nombre d'entrées écrites."""
    entrees = dedoublonner(entrees)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tmp = chemin.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["nom", "type", "programme", "source"])
        w.writeheader()
        w.writerows(entrees)
    os.replace(tmp, chemin)
    par_source: dict[str, int] = {}
    for e in entrees:
        par_source[e["source"]] = par_source.get(e["source"], 0) + 1
    meta = {"maj": datetime.now(timezone.utc).isoformat(timespec="seconds"), "entrees": len(entrees), "sources": par_source}
    chemin.with_name("liste.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(entrees)


def verifier_volume(source: str, entrees: list[dict]) -> None:
    mini = MIN_ENTREES.get(source, 1)
    if len(entrees) < mini:
        raise ValueError(f"{source} : {len(entrees)} entrées seulement (minimum attendu {mini}) — téléchargement refusé.")


def telecharger(url: str, delai: float = 90.0, max_octets: int = 80_000_000) -> str:
    import httpx  # déjà requis par l'assistant IA

    with httpx.stream("GET", url, timeout=delai, follow_redirects=True) as r:
        r.raise_for_status()
        morceaux, total = [], 0
        for bloc in r.iter_bytes():
            total += len(bloc)
            if total > max_octets:
                raise ValueError(f"{url} : fichier anormalement volumineux")
            morceaux.append(bloc)
    return b"".join(morceaux).decode("utf-8", errors="replace")
