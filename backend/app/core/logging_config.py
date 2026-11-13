"""Journalisation structurée (JSON) pour l'industrialisation.

- LOG_FORMAT=json  : une ligne JSON par événement (prêt pour Loki, ELK, CloudWatch, Datadog…) ;
- LOG_FORMAT=text  : format lisible pour le développement (défaut).
Chaque requête HTTP reçoit un identifiant (en-tête X-Request-ID repris ou généré) présent dans tous
les logs émis pendant son traitement et renvoyé dans la réponse, pour corréler support et logs.
"""
from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_RESERVES = set(vars(logging.LogRecord("", 0, "", 0, "", (), None)).keys()) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
            "niveau": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        # Champs additionnels passés via logger.info("...", extra={"mission": 3})
        for k, v in record.__dict__.items():
            if k not in _RESERVES and not k.startswith("_"):
                data[k] = v
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return json.dumps(data, ensure_ascii=False, default=str)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO", fmt: str = "text") -> None:
    """Installe un unique handler sur stdout (le conteneur/orchestrateur collecte stdout)."""
    handler = logging.StreamHandler(sys.stdout)
    if fmt.lower() == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s"))
        handler.addFilter(_RequestIdFilter())
    racine = logging.getLogger()
    racine.handlers[:] = [handler]
    racine.setLevel(level.upper())
    # uvicorn : on laisse remonter vers la racine pour un format unique
    for nom in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(nom)
        lg.handlers[:] = []
        lg.propagate = True
    logging.getLogger("uvicorn.access").handlers[:] = []
    logging.getLogger("uvicorn.access").propagate = False  # remplacé par le log d'accès applicatif
