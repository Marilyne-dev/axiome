"""Envoi d'e-mails : SMTP si configuré, sinon dépôt dans la boîte d'envoi (hors-ligne)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.auth_token import OutboxEmail


def envoyer(db: Session, destinataire: str, sujet: str, corps: str, lien: str = "") -> OutboxEmail:
    """Envoie un e-mail. Toujours archivé dans la boîte d'envoi pour traçabilité."""
    settings = get_settings()
    if settings.smtp_host:
        try:
            _envoyer_smtp(settings, destinataire, sujet, corps)
        except Exception:
            pass  # l'archivage en boîte d'envoi garantit la récupération du lien
    msg = OutboxEmail(destinataire=destinataire, sujet=sujet, corps=corps, lien=lien)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def _envoyer_smtp(settings, destinataire: str, sujet: str, corps: str) -> None:  # pragma: no cover
    import smtplib
    from email.message import EmailMessage

    message = EmailMessage()
    message["From"] = settings.smtp_expediteur
    message["To"] = destinataire
    message["Subject"] = sujet
    message.set_content(corps)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as serveur:
        serveur.starttls()
        if settings.smtp_user:
            serveur.login(settings.smtp_user, settings.smtp_password)
        serveur.send_message(message)
