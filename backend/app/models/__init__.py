"""Agrégation des modèles pour que Base.metadata connaisse toutes les tables.

Importer app.models suffit à enregistrer l'ensemble des tables sur Base.
"""
from app.models.acceptation import Acceptation, LettreMission  # noqa: F401
from app.models.administration import ModeleDocument  # noqa: F401
from app.models.audit import (  # noqa: F401
    AuditLog,
    Confirmation,
    Document,
    Recommendation,
    RiskItem,
    Sample,
    Threshold,
    WorkingPaper,
)
from app.models.auth_token import AuthToken, OutboxEmail  # noqa: F401
from app.models.balance import LigneBalance  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.cabinet import Bureau, Cabinet  # noqa: F401
from app.models.client import Client, Groupe  # noqa: F401
from app.models.client_details import CompteBancaire, Contact, Dirigeant  # noqa: F401
from app.models.controle_interne import ControleInterne, Faiblesse  # noqa: F401
from app.models.csrd import CsrdMateriality, CsrdPoint  # noqa: F401
from app.models.devise import Devise, TauxDeChange  # noqa: F401
from app.models.echantillonnage import SampleItem  # noqa: F401
from app.models.fusion import FusionDossier, FusionEvaluation  # noqa: F401
from app.models.lcbft import DeclarationSoupcon, DossierLCBFT  # noqa: F401
from app.models.mission import Cycle, Mission, MissionDiligence  # noqa: F401
from app.models.planification import AffectationEquipe, Jalon, LigneBudget, PlanMission  # noqa: F401
from app.models.programme import ProcedureAudit, ProgrammeAudit  # noqa: F401
from app.models.referentiel import Referentiel, RegleFiscale  # noqa: F401
from app.models.user import Permission, Role, User  # noqa: F401
from app.models.verification import VerifConcordance, VerifPoint  # noqa: F401

__all__ = [
    "FraudeFecResultat",
    "Base", "User", "Role", "Permission", "Cabinet", "Bureau", "Client", "Groupe",
    "Mission", "Cycle", "Referentiel", "RegleFiscale", "Devise", "TauxDeChange",
    "WorkingPaper", "Document", "RiskItem", "Sample", "Confirmation",
    "Recommendation", "Threshold", "AuditLog", "DossierLCBFT", "DeclarationSoupcon",
    "ModeleDocument", "Contact", "Dirigeant", "CompteBancaire",
    "Acceptation", "LettreMission",
    "PlanMission", "Jalon", "AffectationEquipe", "LigneBudget",
    "ControleInterne", "Faiblesse", "ProgrammeAudit", "ProcedureAudit", "SampleItem",
    "LigneBalance",
]
from app.models.analyse_tva import LigneTVA  # noqa: E402,F401
from app.models.balance_agee import BalanceAgee  # noqa: E402,F401
from app.models.billing import Abonnement, Paiement, Plan  # noqa: E402,F401
from app.models.cadrage_dsn import LigneCadrageDSN  # noqa: E402,F401
from app.models.conclusion import CycleConclusion  # noqa: E402,F401
from app.models.edition import RapportEdition  # noqa: E402,F401
from app.models.fraude_fec import FraudeFecResultat  # noqa: E402,F401
from app.models.rapprochement import RapprochementBancaire  # noqa: E402,F401
from app.models.veille import VeilleReglementaire  # noqa: E402,F401

from app.models.conversation_ia import ConversationIA, MessageIA  # noqa: E402,F401
