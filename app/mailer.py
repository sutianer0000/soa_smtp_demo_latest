"""Send mail through Gmail SMTP, authenticating with an OAuth 2.0 access token (SASL XOAUTH2)."""
import base64
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def xoauth2_string(email: str, access_token: str) -> str:
    # Format defined by Google: base64("user=<email>^Aauth=Bearer <token>^A^A"), ^A = \x01
    raw = f"user={email}\x01auth=Bearer {access_token}\x01\x01"
    return base64.b64encode(raw.encode()).decode()


def send_mail(sender, access_token, to, subject, html, in_reply_to=None) -> str:
    """Send an HTML email as `sender`. Returns its Message-ID so replies can be threaded."""
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=sender.split("@")[1])
    if in_reply_to:
        # These two headers make Gmail show the reply in the same thread as the original.
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(html, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()  # encrypt the connection before sending the token
        smtp.ehlo()
        code, resp = smtp.docmd("AUTH", "XOAUTH2 " + xoauth2_string(sender, access_token))
        if code == 334:
            # Gmail rejected the token: it sends a base64 JSON error and waits for an empty line.
            detail = base64.b64decode(resp).decode()
            smtp.docmd("")
            raise RuntimeError(f"Gmail rejected XOAUTH2 login: {detail}")
        if code != 235:
            raise RuntimeError(f"Gmail SMTP AUTH failed ({code}): {resp.decode()}")
        smtp.send_message(msg)

    return msg["Message-ID"]
