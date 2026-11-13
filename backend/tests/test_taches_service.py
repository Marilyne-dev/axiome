import time

from app.services import taches_service as t


def _attendre(tid, uid, statut_final, delai=5):
    fin = time.time() + delai
    while time.time() < fin:
        e = t.etat(tid, uid)
        if e and e["statut"] == statut_final:
            return e
        time.sleep(0.05)
    raise AssertionError(f"statut {statut_final} non atteint : {t.etat(tid, uid)}")


def test_tache_reussie_et_isolation_proprietaire(tmp_path):
    t.configurer(tmp_path)
    tid = t.lancer(lambda: (b"PK-contenu", "x.xlsx", "application/x"), proprietaire=7, libelle="test")
    e = _attendre(tid, 7, "termine")
    assert e["fichier"] == "x.xlsx" and e["taille"] == 10 and "proprietaire" not in e
    assert t.resultat(tid, 7) == (b"PK-contenu", "x.xlsx", "application/x")
    assert t.etat(tid, 8) is None and t.resultat(tid, 8) is None          # autre utilisateur
    assert t.etat(tid, 8, superadmin=True)["statut"] == "termine"          # éditeur


def test_tache_en_echec_restitue_l_erreur(tmp_path):
    t.configurer(tmp_path)

    def boom():
        raise RuntimeError("fichier corrompu")

    tid = t.lancer(boom, 1, "boom")
    e = _attendre(tid, 1, "echec")
    assert "fichier corrompu" in e["erreur"]
    assert t.resultat(tid, 1) is None


def test_identifiant_malveillant_et_inconnu(tmp_path):
    t.configurer(tmp_path)
    assert t.etat("../../etc/passwd", 1) is None
    assert t.etat("abcdef", 1) is None


def test_tache_orpheline_declaree_en_echec(tmp_path):
    t.configurer(tmp_path)
    t._ecrire_etat("abc123", {"id": "abc123", "statut": "en_cours", "proprietaire": 1, "debut": time.time() - t.DELAI_MAX_S - 5})
    assert t.etat("abc123", 1)["statut"] == "echec"
