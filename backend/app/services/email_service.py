import email.utils
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import socket
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when an email fails to dispatch through the configured provider."""
    pass


class EmailService:
    _sent_emails: List[Dict[str, Any]] = []

    @staticmethod
    def mask_email(email_str: str) -> str:
        """Safely masks an email address for logging and UI presentation."""
        if not email_str or "@" not in email_str:
            return "***"
        parts = email_str.split("@", 1)
        local, domain = parts[0], parts[1]
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[:2] + "*" * (len(local) - 2)
        return f"{masked_local}@{domain}"

    @classmethod
    def is_configured(cls) -> bool:
        """Returns True if real SMTP host and credentials are provided."""
        return bool(
            settings.SMTP_HOST
            and settings.SMTP_HOST.strip()
            and settings.resolved_smtp_user
            and settings.resolved_smtp_pass
        )

    @classmethod
    def get_sent_emails(cls) -> List[Dict[str, Any]]:
        return list(cls._sent_emails)

    @classmethod
    def clear_sent_emails(cls) -> None:
        cls._sent_emails.clear()

    @classmethod
    def test_smtp_connection(cls) -> Dict[str, Any]:
        """
        Tests the SMTP server connection and authentication handshake.
        Does not send an email. Safe diagnostic endpoint.
        """
        host = settings.SMTP_HOST or "smtp.gmail.com"
        port = settings.SMTP_PORT or 587
        is_secure = settings.resolved_smtp_secure
        user = settings.resolved_smtp_user
        password = settings.resolved_smtp_pass

        if not user or not password:
            return {
                "success": False,
                "configured": False,
                "host": host,
                "port": port,
                "provider": settings.EMAIL_PROVIDER,
                "message": (
                    "SMTP credentials are not configured. Set SMTP_USER and SMTP_PASS "
                    "(or your 16-character Google App Password) in backend/.env."
                ),
            }

        try:
            if is_secure:
                server = smtplib.SMTP_SSL(host, port, timeout=10.0)
                server.ehlo()
            else:
                server = smtplib.SMTP(host, port, timeout=10.0)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(user, password)
            server.quit()

            masked_user = (
                user if len(user) <= 4 else f"{user[:3]}***@{user.split('@')[-1]}" if "@" in user else "***"
            )

            return {
                "success": True,
                "configured": True,
                "host": host,
                "port": port,
                "user": masked_user,
                "tls": not is_secure,
                "message": f"Successfully connected to {host}:{port} and authenticated as {masked_user}.",
            }
        except smtplib.SMTPAuthenticationError as exc:
            logger.warning(f"SMTP authentication failure for {user}: {exc.smtp_code} - {exc.smtp_error}")
            return {
                "success": False,
                "configured": True,
                "host": host,
                "port": port,
                "error": "Authentication failed",
                "message": (
                    "Gmail rejected the credentials. Ensure 2-Step Verification is ON in your Google "
                    "Account and generate a 16-character App Password (not your regular account password)."
                ),
            }
        except Exception as exc:
            logger.error(f"SMTP connection test error for {host}:{port}: {exc}")
            return {
                "success": False,
                "configured": True,
                "host": host,
                "port": port,
                "error": str(exc),
                "message": f"Failed to connect to SMTP server ({host}:{port}): {str(exc)}",
            }

    @classmethod
    def send_email(
        cls,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> bool:
        """
        Sends an email via real Gmail SMTP with TLS/STARTTLS.
        Raises EmailDeliveryError if SMTP is unconfigured or if delivery fails.
        In test mode (EMAIL_PROVIDER='test'), safely captures email in-memory.
        """
        email_record = {
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
            "provider": settings.EMAIL_PROVIDER,
        }
        cls._sent_emails.append(email_record)

        # 1. In unit tests, record email and return success
        if settings.EMAIL_PROVIDER == "test":
            logger.info(f"[EmailService - Test Mode] Captured email to {cls.mask_email(to_email)} with subject '{subject}'")
            return True

        # 2. If SMTP credentials are missing in real / production mode, reject with clear instructions
        if not cls.is_configured():
            masked_dest = cls.mask_email(to_email)
            logger.error(
                f"[EmailService - Missing Config] Cannot send verification email to {masked_dest}: "
                "Gmail SMTP credentials (SMTP_USER / SMTP_PASS) are not configured in backend/.env."
            )
            raise EmailDeliveryError(
                "Gmail SMTP credentials are not configured in backend/.env. "
                "Please set SMTP_USER (your Gmail address) and SMTP_PASS (16-character Google App Password) "
                "to deliver verification emails."
            )

        from_addr = settings.resolved_smtp_from
        smtp_user = settings.resolved_smtp_user
        smtp_pass = settings.resolved_smtp_pass
        is_secure = settings.resolved_smtp_secure
        masked_dest = cls.mask_email(to_email)
        masked_user = cls.mask_email(smtp_user)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_addr
            msg["To"] = to_email
            msg["Date"] = email.utils.formatdate(localtime=True)
            msg["Message-ID"] = email.utils.make_msgid(domain="analyticx.ai")

            # Attach plain text and HTML parts
            part_text = MIMEText(text_body, "plain", "utf-8")
            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_text)
            msg.attach(part_html)

            logger.info(
                f"[EmailService - Dispatching] Sending email to {masked_dest} via "
                f"{settings.SMTP_HOST}:{settings.SMTP_PORT} (sender: {masked_user})..."
            )

            if is_secure:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12.0)
                server.ehlo()
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=12.0)
                server.ehlo()
                server.starttls()
                server.ehlo()

            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, [to_email], msg.as_string())
            server.quit()
            logger.info(f"[EmailService - Success] Dispatched transactional email to {masked_dest} via Gmail SMTP.")
            return True
        except smtplib.SMTPAuthenticationError as exc:
            logger.error(f"[EmailService - Auth Failure] Gmail SMTP authentication failed for {masked_user}: {exc.smtp_code}")
            raise EmailDeliveryError(
                "Gmail SMTP authentication failed. Please ensure you are using a 16-character Google App Password "
                "(not your standard Google account password) and 2-Step Verification is active on your Google account."
            ) from exc
        except (smtplib.SMTPConnectError, ConnectionRefusedError, TimeoutError, socket.gaierror, OSError) as exc:
            logger.error(f"[EmailService - Connection Failure] SMTP connection to {settings.SMTP_HOST}:{settings.SMTP_PORT} failed: {exc}")
            raise EmailDeliveryError(
                f"Could not connect to Gmail SMTP server ({settings.SMTP_HOST}:{settings.SMTP_PORT}): {exc}. "
                "Please verify internet connectivity and port 587 access."
            ) from exc
        except Exception as exc:
            logger.error(f"[EmailService - Delivery Error] Gmail SMTP delivery to {masked_dest} failed: {exc}", exc_info=False)
            raise EmailDeliveryError(
                f"Failed to deliver email through Gmail SMTP: {str(exc)}"
            ) from exc

    @classmethod
    def send_otp_email(cls, to_email: str, otp_code: str, purpose: str = "login") -> bool:
        """Sends a branded 6-digit verification code email."""
        expiry_minutes = settings.resolved_otp_expiry_minutes
        purpose_label = "Account Verification"
        action_verb = "sign in to"
        if purpose == "signup":
            purpose_label = "Welcome to Analyticx AI"
            action_verb = "complete your registration for"
        elif purpose == "link":
            purpose_label = "Link Google Account"
            action_verb = "link your Google identity to"
        elif purpose == "reset":
            purpose_label = "Password Reset Verification"
            action_verb = "reset your password for"

        subject = f"Your Analyticx AI Verification Code: {otp_code}"

        text_body = f"""Analyticx AI — {purpose_label}

Your one-time verification code is: {otp_code}

Use this code to {action_verb} your Analyticx AI workspace.
This code expires in {expiry_minutes} minutes and can only be used once.

Security Notice:
Never share this code with anyone. Analyticx AI support will never ask for your verification code.
If you did not request this email, please ignore it.
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Analyticx AI Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f1f5f9;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0b0f19; padding: 40px 20px;">
    <tr>
      <td align="center">
        <!-- Main Card -->
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #111827; border: 1px solid #1e293b; border-radius: 20px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);">
          <!-- Top Accent Gradient Bar -->
          <tr>
            <td height="4" style="background: linear-gradient(90deg, #06b6d4 0%, #3b82f6 100%);"></td>
          </tr>

          <!-- Card Content -->
          <tr>
            <td style="padding: 40px 36px;">
              <!-- Header / Logo -->
              <table width="100%" border="0" cellspacing="0" cellpadding="0" style="margin-bottom: 28px;">
                <tr>
                  <td>
                    <div style="display: inline-block; background: linear-gradient(135deg, #06b6d4, #3b82f6); padding: 8px 14px; border-radius: 10px; font-size: 14px; font-weight: 800; color: #020617; letter-spacing: 0.5px;">
                      ANALYTICX AI
                    </div>
                  </td>
                  <td align="right">
                    <span style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #06b6d4; font-weight: 600; background: rgba(6, 182, 212, 0.1); border: 1px solid rgba(6, 182, 212, 0.2); padding: 4px 10px; border-radius: 9999px;">
                      {purpose_label}
                    </span>
                  </td>
                </tr>
              </table>

              <!-- Main Heading -->
              <h1 style="margin: 0 0 10px 0; font-size: 22px; font-weight: 700; color: #f8fafc; letter-spacing: -0.5px;">
                Verification Code
              </h1>
              <p style="margin: 0 0 28px 0; font-size: 14px; line-height: 22px; color: #94a3b8;">
                Use the one-time code below to {action_verb} your personalized <strong style="color: #38bdf8;">Analyticx AI</strong> account.
              </p>

              <!-- OTP Digits Box -->
              <div style="background-color: #030712; border: 1px solid #1e293b; border-radius: 14px; padding: 22px; text-align: center; margin-bottom: 24px;">
                <div style="font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 36px; font-weight: 800; letter-spacing: 12px; color: #38bdf8; text-indent: 12px;">
                  {otp_code}
                </div>
                <div style="margin-top: 10px; font-size: 12px; color: #64748b; font-weight: 500;">
                  ⏱️ Expires in <strong style="color: #cbd5e1;">{expiry_minutes} minutes</strong> • Single use only
                </div>
              </div>

              <!-- Security Information Note -->
              <div style="background-color: rgba(30, 41, 59, 0.5); border-left: 3px solid #06b6d4; border-radius: 6px; padding: 12px 16px; margin-bottom: 28px;">
                <p style="margin: 0; font-size: 12px; line-height: 18px; color: #94a3b8;">
                  <strong style="color: #f1f5f9;">Security Tip:</strong> Analyticx AI will never ask for your verification code by phone, chat, or external message. Do not share this code with anyone.
                </p>
              </div>

              <!-- Footer info -->
              <p style="margin: 0; font-size: 12px; line-height: 18px; color: #64748b;">
                If you did not make this request, you can safely disregard this email. Your account remains protected.
              </p>
            </td>
          </tr>

          <!-- Footer Bar -->
          <tr>
            <td style="padding: 20px 36px; background-color: #0a0e17; border-top: 1px solid #1e293b; text-align: center;">
              <p style="margin: 0; font-size: 11px; color: #475569;">
                &copy; {email.utils.formatdate(localtime=True).split(' ')[3]} Analyticx AI Inc. • Enterprise Business Intelligence & Predictive Analytics
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        return cls.send_email(to_email, subject, html_body, text_body)


email_service = EmailService()
