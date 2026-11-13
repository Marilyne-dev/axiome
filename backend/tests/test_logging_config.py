import json
import logging

from app.core import logging_config as lc


def _enregistrement(**extra):
    r = logging.LogRecord("axiome.test", logging.INFO, __file__, 1, "bonjour %s", ("monde",), None)
    r.__dict__.update(extra)
    return r


def test_json_une_ligne_avec_request_id_et_champs_supplementaires():
    jeton = lc.request_id_var.set("req-42")
    try:
        ligne = lc.JsonFormatter().format(_enregistrement(statut=200, duree_ms=3.2))
    finally:
        lc.request_id_var.reset(jeton)
    d = json.loads(ligne)
    assert "\n" not in ligne
    assert d["message"] == "bonjour monde" and d["request_id"] == "req-42"
    assert d["statut"] == 200 and d["duree_ms"] == 3.2 and d["niveau"] == "INFO"


def test_json_exception_serialisee():
    try:
        raise ValueError("x")
    except ValueError:
        import sys
        r = _enregistrement()
        r.exc_info = sys.exc_info()
    assert "ValueError" in json.loads(lc.JsonFormatter().format(r))["exception"]
