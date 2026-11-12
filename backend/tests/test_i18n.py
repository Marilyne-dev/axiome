"""Phase 7 — i18n : parité des catalogues + bascule FR/EN de la chrome."""
from __future__ import annotations

from _helpers_ecrans import ck, mission

from app.core.i18n import CATALOG, t


def test_catalogues_symetriques_et_non_vides():
    fr, en = CATALOG["fr"], CATALOG["en"]
    assert set(fr) == set(en), "clés FR/EN désymétrisées"
    assert all(v.strip() for v in fr.values()), "valeur FR vide"
    assert all(v.strip() for v in en.values()), "valeur EN vide"


def test_traduction_repli_sur_cle_inconnue():
    assert t("page.acceptation", "en") == "Client acceptance & continuance"
    assert t("cle.inexistante", "en") == "cle.inexistante"  # repli sur la clé brute


def test_bascule_langue_et_rendu_anglais(client, db_session):
    mid = mission(db_session)
    c = ck(client)
    # page en FR par défaut
    r_fr = client.get(f"/missions/{mid}/vue/acceptation", cookies=c)
    assert "maintien de la mission" in r_fr.text
    # bascule EN (persistée sur l'utilisateur) puis re-rendu
    client.get("/vue/langue/en", cookies=c, follow_redirects=False)
    r_en = client.get(f"/missions/{mid}/vue/acceptation", cookies=c)
    assert "Client acceptance" in r_en.text and "continuance" in r_en.text
    assert "← File" in r_en.text  # chrome traduite
