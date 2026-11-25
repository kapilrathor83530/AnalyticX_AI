#!/usr/bin/env python3
"""
Analyticx AI — Gmail SMTP Live Diagnostics & Connection Smoke-Test CLI

Usage:
    python backend/scripts/test_smtp_live.py
    python backend/scripts/test_smtp_live.py --to your_email@example.com
"""

import argparse
import os
from pathlib import Path
import smtplib
import socket
import sys

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load backend/.env
env_path = backend_dir / ".env"
load_dotenv(dotenv_path=env_path, override=True)

from app.core.config import settings
from app.services.email_service import EmailService


def mask(s: str) -> str:
    if not s or "@" not in s:
        return "***" if s else "(empty)"
    parts = s.split("@", 1)
    loc, dom = parts[0], parts[1]
    if len(loc) <= 2:
        return loc[0] + "*@" + dom
    return loc[:2] + "*" * (len(loc) - 2) + "@" + dom


def run_diagnostics(test_recipient: str | None = None) -> int:
    print("=" * 70)
    print(" ANALYTICX AI — GMAIL SMTP LIVE DIAGNOSTICS & SMOKE TEST")
    print("=" * 70)

    host = settings.SMTP_HOST or "smtp.gmail.com"
    port = settings.SMTP_PORT or 587
    user = settings.resolved_smtp_user
    password = settings.resolved_smtp_pass
    from_addr = settings.resolved_smtp_from
    is_secure = settings.resolved_smtp_secure

    print(f"[*] Configuration Source: {env_path}")
    print(f"[*] SMTP Provider:        {settings.EMAIL_PROVIDER}")
    print(f"[*] Target Host & Port:   {host}:{port}")
    print(f"[*] STARTTLS / SSL:       {'Port 465 (Direct SSL)' if is_secure else 'Port 587 (Explicit STARTTLS)'}")
    print(f"[*] Configured Sender:    {from_addr}")
    print(f"[*] SMTP Username:        {mask(user)}")
    print(f"[*] SMTP Password:        {'[CONFIGURED - ' + str(len(password)) + ' chars]' if password else '[NOT SET]'}")
    print("-" * 70)

    if not user or not password:
        print("\n[!] STATUS: GMAIL SMTP CREDENTIALS NOT CONFIGURED")
        print("\nTo send real verification emails to users' inboxes:")
        print("  1. Go to your Google Account: https://myaccount.google.com/security")
        print("  2. Ensure '2-Step Verification' is turned ON.")
        print("  3. Open 'App Passwords': https://myaccount.google.com/apppasswords")
        print("  4. Generate a 16-character App Password for 'Analyticx AI'.")
        print("  5. Open 'backend/.env' and set:")
        print("     SMTP_USER=your_gmail@gmail.com")
        print("     SMTP_PASS=xxxx xxxx xxxx xxxx   (your 16-character Google App Password)")
        print("     SMTP_FROM=\"Analyticx AI <your_gmail@gmail.com>\"")
        print("\nOnce saved, rerun this script to verify the connection.\n")
        return 1

    print("[1/3] Resolving DNS and establishing TCP socket...")
    try:
        sock = socket.create_connection((host, port), timeout=8.0)
        sock.close()
        print(f"      [OK] Socket connected to {host}:{port}")
    except Exception as exc:
        print(f"      [FAIL] Could not connect to {host}:{port}: {exc}")
        print("      Check your internet connection and verify port 587 is not blocked by firewall.")
        return 1

    print("[2/3] Performing SMTP Handshake and TLS Negotiation...")
    try:
        if is_secure:
            server = smtplib.SMTP_SSL(host, port, timeout=10.0)
            server.ehlo()
        else:
            server = smtplib.SMTP(host, port, timeout=10.0)
            server.ehlo()
            print("      Executing STARTTLS...")
            server.starttls()
            server.ehlo()
        print("      [OK] TLS handshake established successfully.")

        print(f"[3/3] Authenticating as {mask(user)}...")
        server.login(user, password)
        print("      [OK] Gmail SMTP Authentication SUCCEEDED!")
        server.quit()
    except smtplib.SMTPAuthenticationError as exc:
        print(f"      [FAIL] Authentication rejected: {exc.smtp_code} - {exc.smtp_error.decode('utf-8', errors='ignore')}")
        print("\n  >> Ensure you are using a 16-character Google 'App Password' (not your primary password).")
        print("  >> Ensure 2-Step Verification is active on the Google Account.")
        return 1
    except Exception as exc:
        print(f"      [FAIL] SMTP handshake error: {exc}")
        return 1

    print("\n" + "=" * 70)
    print(" ALL CHECKS PASSED: Gmail SMTP is ready for transactional OTP delivery.")
    print("=" * 70)

    if test_recipient:
        print(f"\n[*] Dispatching live test OTP email to: {test_recipient}...")
        try:
            EmailService.send_otp_email(to_email=test_recipient, otp_code="849201", purpose="login")
            print(f"[+] SUCCESS: Test verification code sent to {test_recipient}. Check your inbox!")
        except Exception as exc:
            print(f"[-] Email delivery failed: {exc}")
            return 1

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyticx AI Gmail SMTP Diagnostics")
    parser.add_argument("--to", help="Optional recipient email to send a real test verification code", default=None)
    args = parser.parse_args()
    sys.exit(run_diagnostics(args.to))
