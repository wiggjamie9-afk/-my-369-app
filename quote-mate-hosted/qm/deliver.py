"""Getting a new lead to the tradie: an email, and optionally a copy posted to their own webhook.
Both run after the homeowner has their "thanks" screen, so a slow mail server never slows the form."""
import ipaddress
import json
import smtplib
import socket
import ssl
import urllib.parse
import urllib.request
from email.message import EmailMessage

from .estimate import money


def mail_settings(env):
    """SMTP details from the environment, or None when email is not set up. Nothing is stored in the repo."""
    if not env.get("SMTP_HOST") or not env.get("SMTP_FROM"):
        return None
    return {"host": env["SMTP_HOST"], "port": int(env.get("SMTP_PORT") or 587), "user": env.get("SMTP_USER", ""),
            "password": env.get("SMTP_PASSWORD", ""), "sender": env["SMTP_FROM"],
            "tls": env.get("SMTP_TLS", "starttls").lower()}          # starttls | ssl | none


def send_email(smtp, to, subject, body, reply_to=""):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = smtp["sender"], to, subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    if smtp["tls"] == "ssl":
        server = smtplib.SMTP_SSL(smtp["host"], smtp["port"], timeout=20, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(smtp["host"], smtp["port"], timeout=20)
    try:
        if smtp["tls"] == "starttls":
            server.starttls(context=ssl.create_default_context())
        if smtp["user"]:
            server.login(smtp["user"], smtp["password"])
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except smtplib.SMTPException:
            pass


def lead_email(tenant, lead, lead_url):
    """(subject, body) for the new-lead email. No header can be injected: every value is single-line."""
    one = lambda v: " ".join(str(v).split())
    subject = "New quote request: %s, %s" % (one(lead["name"]), one(lead["suburb"]))
    body = "\n".join([
        "New quote request for %s" % one(tenant["name"]), "",
        "Name:     %s" % one(lead["name"]),
        "Phone:    %s" % one(lead["phone"]),
        "Email:    %s" % one(lead["email"]),
        "Suburb:   %s" % one(lead["suburb"]), "",
        "Job:      %s, %s, %s" % (one(lead["job_type"]), one(lead["difficulty"]), one(lead["size"])),
        "Ballpark: %s to %s inc GST (what they were shown)" % (money(lead["low"]), money(lead["high"])),
        "Photos:   %d" % lead.get("photos", 0), "",
        "Open it:  %s" % lead_url, ""])
    return subject[:150], body


def safe_public_url(url, allow_private=False):
    """Only https, and only to a public address. Stops a webhook setting being used to reach
    this server's own network (a customer could otherwise point it at an internal service)."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" and not (allow_private and parts.scheme == "http"):
        raise ValueError("the webhook address must start with https://")
    if not parts.hostname or parts.username or parts.password:
        raise ValueError("that webhook address isn't valid")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError("that webhook address can't be found")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not allow_private and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise ValueError("the webhook address must be on the public internet")
    return url


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None                       # a redirect could point somewhere private: don't follow


def forward(url, payload, allow_private=False):
    safe_public_url(url, allow_private)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json",
                                                                                  "User-Agent": "QuoteMate/1"})
    with urllib.request.build_opener(_NoRedirect).open(req, timeout=15) as r:
        if not 200 <= r.status < 300:
            raise ValueError("webhook answered %d" % r.status)
