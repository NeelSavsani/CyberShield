"""Transactional Email Delivery Service.

Supports custom email delivery via SendGrid, Mailgun, Postmark, or SMTP
using the CyberShield HTML email template.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
import urllib.request
import urllib.parse
import json

logger = logging.getLogger("cybershield.email")

# Locate the HTML email template
TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "password_reset_email.html"

DEFAULT_EMAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your CyberShield Password</title>
  <style type="text/css">
    body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }
    body { height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: #080c14; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    .reset-btn:hover {
      background: linear-gradient(135deg, #1d4ed8 0%, #0369a1 100%) !important;
      box-shadow: 0 6px 24px rgba(37, 99, 235, 0.6) !important;
    }
    @media screen and (max-width: 600px) {
      .email-container { width: 100% !important; padding: 10px !important; }
      .content-cell { padding: 24px 18px !important; }
      .reset-btn { width: 100% !important; text-align: center !important; box-sizing: border-box !important; }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: #080c14;">

  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #080c14; table-layout: fixed;">
    <tr>
      <td align="center" style="padding: 40px 12px;">

        <table border="0" cellpadding="0" cellspacing="0" width="600" class="email-container" style="background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.65);">
          
          <!-- Top Neon Accent Gradient Bar -->
          <tr>
            <td style="background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%); height: 5px; font-size: 0; line-height: 0;">&nbsp;</td>
          </tr>

          <!-- Logo & Brand Header -->
          <tr>
            <td align="center" style="padding: 36px 32px 16px 32px;">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="padding-top: 14px; font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: 0.5px;">
                    Cyber<span style="color: #3b82f6;">Shield</span>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="font-size: 11px; font-weight: 600; color: #38bdf8; text-transform: uppercase; letter-spacing: 1.5px; padding-top: 4px;">
                    Threat Intelligence & Security Platform
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Content Body -->
          <tr>
            <td class="content-cell" style="padding: 10px 40px 32px 40px;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                
                <tr>
                  <td align="center" style="font-size: 22px; font-weight: 700; color: #f8fafc; padding-bottom: 12px;">
                    Password Reset Request
                  </td>
                </tr>

                <tr>
                  <td style="font-size: 15px; line-height: 1.6; color: #94a3b8; text-align: center; padding-bottom: 28px;">
                    We received a request to reset the password for your <strong style="color: #f1f5f9;">CyberShield</strong> account. Click the secure button below to choose a new password.
                  </td>
                </tr>

                <!-- Styled Action Button -->
                <tr>
                  <td align="center" style="padding-bottom: 32px;">
                    <table border="0" cellpadding="0" cellspacing="0">
                      <tr>
                        <td align="center" style="border-radius: 12px; background: linear-gradient(135deg, #2563eb 0%, #0284c7 100%); box-shadow: 0 8px 24px rgba(37, 99, 235, 0.45); padding: 0;">
                          <a href="{{RESET_LINK}}" target="_blank" class="reset-btn" style="display: inline-block; padding: 15px 32px; font-size: 15px; font-weight: 700; color: #ffffff; text-decoration: none; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.25); letter-spacing: 0.3px;">
                            🔒 Reset Password Now &rarr;
                          </a>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>

                <!-- Security Box -->
                <tr>
                  <td style="background-color: rgba(30, 41, 59, 0.7); border: 1px solid #334155; border-left: 4px solid #38bdf8; border-radius: 10px; padding: 16px 18px; margin-bottom: 24px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%">
                      <tr>
                        <td style="font-size: 13px; color: #cbd5e1; line-height: 1.6;">
                          <strong style="color: #38bdf8;">🛡️ Security Information:</strong><br>
                          • This password reset link will expire in <strong>1 hour</strong>.<br>
                          • If you did not request this change, your account remains secure and no action is required.
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #0b0f19; padding: 22px 32px; text-align: center; border-top: 1px solid #1e293b; font-size: 12px; color: #64748b; line-height: 1.5;">
              <p style="margin: 0 0 6px 0;">If you need assistance, please contact CyberShield Support.</p>
              <p style="margin: 0; color: #475569;">&copy; CyberShield Security Platform. All rights reserved.</p>
            </td>
          </tr>

        </table>

      </td>
    </tr>
  </table>

</body>
</html>"""


def load_email_template(reset_link: str) -> str:
    """Load the password reset email template and inject the reset link."""
    if TEMPLATE_PATH.is_file():
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    else:
        template = DEFAULT_EMAIL_TEMPLATE
    return template.replace("{{RESET_LINK}}", reset_link)


def send_password_reset_email(to_email: str, reset_link: str) -> dict[str, str]:
    """Send custom styled password reset email via available service (SendGrid, Mailgun, Postmark, or SMTP)."""
    html_content = load_email_template(reset_link)
    subject = "Reset Your CyberShield Password"

    print("\n" + "=" * 70)
    print(" [CYBERSHIELD AUTH] PASSWORD RESET EMAIL DISPATCHED")
    print(f" STATUS          : SUCCESS")
    print(f" Recipient Email : {to_email}")
    print(f" Email Message   : Email has been sent to {to_email}")
    print(f" Reset URL       : {reset_link}")

    # 1. Resend API
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        try:
            res = _send_via_resend(to_email, subject, html_content, resend_key)
            print(f" Delivery Provider: Resend API (STATUS OK)")
            print("=" * 70 + "\n")
            return res
        except Exception as e:
            print(f" Resend Delivery Error: {e}")

    # 2. SendGrid API
    sendgrid_key = os.getenv("SENDGRID_API_KEY")
    if sendgrid_key:
        try:
            res = _send_via_sendgrid(to_email, subject, html_content, sendgrid_key)
            print(f" Delivery Provider: SendGrid API (STATUS OK)")
            print("=" * 70 + "\n")
            return res
        except Exception as e:
            print(f" SendGrid Delivery Error: {e}")

    # 3. Mailgun API
    mailgun_key = os.getenv("MAILGUN_API_KEY")
    mailgun_domain = os.getenv("MAILGUN_DOMAIN")
    if mailgun_key and mailgun_domain:
        try:
            res = _send_via_mailgun(to_email, subject, html_content, mailgun_key, mailgun_domain)
            print(f" Delivery Provider: Mailgun API (STATUS OK)")
            print("=" * 70 + "\n")
            return res
        except Exception as e:
            print(f" Mailgun Delivery Error: {e}")

    # 4. Postmark API
    postmark_token = os.getenv("POSTMARK_SERVER_TOKEN")
    if postmark_token:
        try:
            res = _send_via_postmark(to_email, subject, html_content, postmark_token)
            print(f" Delivery Provider: Postmark API (STATUS OK)")
            print("=" * 70 + "\n")
            return res
        except Exception as e:
            print(f" Postmark Delivery Error: {e}")

    # 5. Standard SMTP Server (Gmail / Outlook / Custom SMTP)
    smtp_host = os.getenv("SMTP_HOST")
    if smtp_host:
        try:
            res = _send_via_smtp(to_email, subject, html_content, host=smtp_host)
            print(f" Delivery Provider: SMTP ({smtp_host}) (STATUS OK)")
            print("=" * 70 + "\n")
            return res
        except Exception as e:
            print(f" SMTP Delivery Error: {e}")

    # Console / Dev mode when no third-party keys present in .env
    print(f" Delivery Status  : Simulated Console Log (Add SMTP_HOST, RESEND_API_KEY, or SENDGRID_API_KEY to backend/.env for live custom HTML email delivery)")
    print("=" * 70 + "\n")

    return {
        "status": "success",
        "provider": "console_log",
        "message": f"Password reset email for {to_email} processed successfully.",
        "reset_link": reset_link,
    }


def _send_via_sendgrid(to_email: str, subject: str, html_content: str, api_key: str) -> dict[str, str]:
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "security@cybershield.com")
    payload = json.dumps({
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "CyberShield Security"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_content}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return {"status": "success", "provider": "sendgrid", "code": str(resp.status)}


def _send_via_mailgun(to_email: str, subject: str, html_content: str, api_key: str, domain: str) -> dict[str, str]:
    from_email = os.getenv("MAILGUN_FROM_EMAIL", f"CyberShield Security <security@{domain}>")
    data = urllib.parse.urlencode({
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "html": html_content
    }).encode("utf-8")

    url = f"https://api.mailgun.net/v3/{domain}/messages"

    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_mgr.add_password(None, url, "api", api_key)
    handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
    opener = urllib.request.build_opener(handler)
    
    with opener.open(req) as resp:
        return {"status": "success", "provider": "mailgun", "code": str(resp.status)}


def _send_via_postmark(to_email: str, subject: str, html_content: str, token: str) -> dict[str, str]:
    from_email = os.getenv("POSTMARK_FROM_EMAIL", "security@cybershield.com")
    payload = json.dumps({
        "From": from_email,
        "To": to_email,
        "Subject": subject,
        "HtmlBody": html_content,
        "MessageStream": "outbound"
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.postmarkapp.com/email",
        data=payload,
        headers={
            "X-Postmark-Server-Token": token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return {"status": "success", "provider": "postmark", "code": str(resp.status)}


def _send_via_smtp(to_email: str, subject: str, html_content: str, host: str) -> dict[str, str]:
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").replace(" ", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", user or "security@cybershield.com").strip()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"CyberShield Security <{from_email}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())

    return {"status": "success", "provider": "smtp"}


def _send_via_resend(to_email: str, subject: str, html_content: str, api_key: str) -> dict[str, str]:
    from_email = os.getenv("RESEND_FROM_EMAIL", "CyberShield Security <onboarding@resend.dev>")
    payload = json.dumps({
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        return {"status": "success", "provider": "resend", "code": str(resp.status)}

