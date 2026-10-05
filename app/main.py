import secrets
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from . import config, db, mailer, oauth

app = FastAPI(title="Absence Request Demo")
app.add_middleware(SessionMiddleware, secret_key=config.SESSION_SECRET)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def subject_for(req) -> str:
    return f"Absence request: {req['start_date']} to {req['end_date']}"


def current_user(request: Request) -> str | None:
    """Signed-in email, or None. Storage is in memory, so after a server restart the cookie
    may still name a user whose tokens are gone: treat that as signed out."""
    email = request.session.get("email")
    if email and db.get_user(email) is None:
        request.session.clear()
        return None
    return email


@app.get("/")
def home(request: Request):
    email = current_user(request)
    if not email:
        return templates.TemplateResponse(request, "login.html")
    if email in config.MANAGER_EMAILS:
        waiting = [r for r in db.requests_to(email) if r["status"] == "PENDING"]
        return templates.TemplateResponse(request, "manager.html", {"email": email, "waiting": waiting})
    return templates.TemplateResponse(request, "home.html", {"email": email, "sent": db.requests_from(email)})


# --- OAuth 2.0 sign-in -------------------------------------------------------

@app.get("/login")
def login(request: Request, next: str = "/", hint: str | None = None):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state 
    # Only local paths, so /login can't be abused as an open redirect.
    request.session["next"] = next if next.startswith("/") and not next.startswith("//") else "/"
    return RedirectResponse(oauth.authorization_url(state, hint))


@app.get("/auth/callback")
def auth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(400, f"Google sign-in failed: {error}")
    if not code or state != request.session.pop("oauth_state", None):
        raise HTTPException(400, "Invalid OAuth state, please sign in again")
    request.session["email"] = oauth.exchange_code(code)
    return RedirectResponse(request.session.pop("next", "/"))


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")


# --- Worker: send an absence request ----------------------------------------

@app.post("/requests")
def create_request(
    request: Request,
    manager_email: str = Form(),
    start_date: str = Form(),
    end_date: str = Form(),
    reason: str = Form(),
):
    worker = current_user(request)
    if not worker:
        return RedirectResponse("/", status_code=303)

    # Random secret per request: the Yes/No links only work with it, so they can't be guessed.
    token = secrets.token_urlsafe(24)
    req_id = db.create_request(worker, manager_email.strip().lower(), start_date, end_date, reason, token)
    req = db.get_request(req_id)

    link = f"{config.BASE_URL}/requests/{req_id}/decide?t={token}&answer="
    ctx = {"req": req, "yes_url": link + "yes", "no_url": link + "no"}

    message_id = mailer.send_mail(
        sender=worker,
        access_token=oauth.access_token_for(worker),
        to=req["manager_email"],
        subject=subject_for(req),
        html=templates.get_template("email_request.html").render(ctx),
    )
    db.set_message_id(req_id, message_id)
    return RedirectResponse("/", status_code=303)


# --- Manager: click Yes / No in the email ------------------------------------

@app.get("/requests/{req_id}/decide")
def decide(request: Request, req_id: int, answer: str, t: str):
    req = db.get_request(req_id)
    if req is None or not secrets.compare_digest(req["token"], t) or answer not in ("yes", "no"):
        raise HTTPException(404, "Request not found")

    # Only the manager the email was sent to may answer: sign them in first if needed.
    manager = req["manager_email"]
    if current_user(request) != manager:
        back_here = f"{request.url.path}?{request.url.query}"
        return RedirectResponse(f"/login?next={quote(back_here)}&hint={quote(manager)}")

    if req["status"] == "PENDING":
        status = "APPROVED" if answer == "yes" else "REJECTED"
        # Reply from the manager's own Gmail, in the same thread as the request.
        mailer.send_mail(
            sender=manager,
            access_token=oauth.access_token_for(manager),
            to=req["worker_email"],
            subject="Re: " + subject_for(req),
            html=templates.get_template("email_reply.html").render(req=req, status=status),
            in_reply_to=req["message_id"],
        )
        db.set_status(req_id, status)
        req = db.get_request(req_id)

    return templates.TemplateResponse(request, "decided.html", {"req": req})
