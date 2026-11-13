"""Commande : met à jour storage/sanctions/liste.csv depuis les listes officielles.

    python -m app.tools.maj_sanctions [--ofac] [--onu] [--csv-local fichier.csv ...]

À planifier (cron / tâche planifiée) une fois par jour. Code de sortie 1 si la mise à jour échoue
(la liste précédente est alors conservée).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import settings
from app.services import sanctions_sync as s


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ofac", action="store_true", help="liste OFAC/SDN (États-Unis)")
    p.add_argument("--onu", action="store_true", help="liste consolidée du Conseil de sécurité de l'ONU")
    p.add_argument("--csv-local", nargs="*", default=[], help="fichiers CSV supplémentaires (ex. export UE)")
    a = p.parse_args(argv)
    if not (a.ofac or a.onu or a.csv_local):
        a.ofac = a.onu = True

    entrees: list[dict] = []
    try:
        if a.ofac:
            e = s.parse_ofac_sdn(s.telecharger(s.URL_OFAC_SDN), s.telecharger(s.URL_OFAC_ALT))
            s.verifier_volume("OFAC", e)
            entrees += e
            print(f"OFAC : {len(e)} entrées")
        if a.onu:
            e = s.parse_onu_xml(s.telecharger(s.URL_ONU))
            s.verifier_volume("ONU", e)
            entrees += e
            print(f"ONU  : {len(e)} entrées")
        for f in a.csv_local:
            e = s.parse_csv_local(Path(f).read_text(encoding="utf-8"), source=Path(f).stem)
            entrees += e
            print(f"{f} : {len(e)} entrées")
    except Exception as exc:  # noqa: BLE001
        print(f"ÉCHEC : {exc}\nLa liste précédente est conservée.", file=sys.stderr)
        return 1

    chemin = Path(settings.storage_dir) / "sanctions" / "liste.csv"
    n = s.ecrire_liste(entrees, chemin)
    print(f"{n} entrées écrites dans {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
