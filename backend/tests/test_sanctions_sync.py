from pathlib import Path

import pytest

from app.services import sanctions_sync as s

SDN = (
    '36,"AEROCARIBBEAN AIRLINES","-0- ","CUBA",-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- ,-0- \n'
    '306,"BANCO NACIONAL DE CUBA","-0- ","CUBA",-0- ,-0- \n'
    '1234,"DOE, John","individual","UKRAINE-EO13660",-0- ,-0- \n'
    '9999,"MV EXEMPLE","vessel","SDGT",-0- ,-0- \n'
    "ligne invalide\n"
)
ALT = '1234,5,"aka","DOE, Johnny",-0- \n77777,1,"aka","ORPHELIN",-0- \n'

ONU = """<?xml version="1.0"?><CONSOLIDATED_LIST><INDIVIDUALS>
<INDIVIDUAL><FIRST_NAME>Ali</FIRST_NAME><SECOND_NAME>Ben</SECOND_NAME><UN_LIST_TYPE>Al-Qaida</UN_LIST_TYPE>
<INDIVIDUAL_ALIAS><ALIAS_NAME>Abu Ali</ALIAS_NAME></INDIVIDUAL_ALIAS><INDIVIDUAL_ALIAS><ALIAS_NAME/></INDIVIDUAL_ALIAS></INDIVIDUAL>
</INDIVIDUALS><ENTITIES><ENTITY><FIRST_NAME>Societe Fantome</FIRST_NAME><UN_LIST_TYPE>DPRK</UN_LIST_TYPE>
<ENTITY_ALIAS><ALIAS_NAME>Fantome SARL</ALIAS_NAME></ENTITY_ALIAS></ENTITY></ENTITIES></CONSOLIDATED_LIST>"""


def test_ofac_types_noms_et_programmes():
    e = s.parse_ofac_sdn(SDN, ALT)
    par_nom = {x["nom"]: x for x in e}
    assert par_nom["AEROCARIBBEAN AIRLINES"]["type"] == "entite"
    assert par_nom["John DOE"]["type"] == "personne"
    assert par_nom["John DOE"]["programme"] == "UKRAINE-EO13660"  # le « 0 » final ne doit pas être tronqué
    assert par_nom["MV EXEMPLE"]["type"] == "vessel"
    assert par_nom["Johnny DOE"]["programme"] == "UKRAINE-EO13660"  # alias hérite du dossier
    assert "ORPHELIN" not in par_nom  # alias sans dossier ignoré
    assert all(x["source"] == "OFAC" for x in e)


def test_onu_individus_entites_alias():
    e = s.parse_onu_xml(ONU)
    noms = {(x["nom"], x["type"]) for x in e}
    assert ("Ali Ben", "personne") in noms and ("Abu Ali", "personne") in noms
    assert ("Societe Fantome", "entite") in noms and ("Fantome SARL", "entite") in noms
    assert len(e) == 4  # alias vide ignoré


def test_ecriture_atomique_dedoublonnage_et_lecture_par_le_service(tmp_path: Path):
    chemin = tmp_path / "sanctions" / "liste.csv"
    entrees = s.parse_ofac_sdn(SDN, ALT) + s.parse_onu_xml(ONU) + [
        {"nom": "john  doe", "type": "personne", "programme": "", "source": "OFAC"}]  # doublon (normalisé)
    n = s.ecrire_liste(entrees, chemin)
    assert n == len(s.dedoublonner(entrees)) < len(entrees)
    assert (chemin.parent / "liste.meta.json").exists()
    assert not list(chemin.parent.glob("*.tmp"))
    lu = s.parse_csv_local(chemin.read_text(encoding="utf-8"), source="x")
    assert {x["nom"] for x in lu} >= {"John DOE", "Ali Ben", "Societe Fantome"}


def test_volume_insuffisant_refuse():
    with pytest.raises(ValueError):
        s.verifier_volume("OFAC", [{"nom": "a"}] * 10)
    s.verifier_volume("AUTRE", [{"nom": "a"}])
