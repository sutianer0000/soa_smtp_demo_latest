# Gmail SMTP + OAuth 2.0: Absence Request Demo

A small FastAPI web app that helps autom

- A **worker** signs in with Google and submits a leave request.
- The app emails the **manager** from the worker's Gmail, through Gmail SMTP.
- The manager clicks **Yes** or **No** in the email.
- The app replies to the worker **from the manager's Gmail**, in the same thread.

Login to Gmail SMTP uses an **OAuth 2.0 access token** (SASL `XOAUTH2`) instead of a password.

---

## 1. Requirements

- Python **3.10+**
- Two Google accounts for the demo: one **worker**, one **manager**.
  - With **Internal** audience (step 2.3), both must belong to the same Google Workspace organization (e.g. `@student.tdtu.edu.vn`).
  - With **External** audience, any Gmail accounts listed as test users.
- Two browser profiles (or one normal window plus one incognito window), so both users can be signed in at the same time.

---

## 2. Google Cloud setup (step by step)

Open <https://console.cloud.google.com> with the account that will own the app.

### 2.1 Create a project
1. Click the project picker at the top → **New Project**.
2. Name it (e.g. `absence-demo`). For an **Internal** app, choose your organization (e.g. `tdtu.edu.vn`) as the location.
3. Click **Create** and make sure the new project is selected.

### 2.2 Enable the Gmail API
1. **APIs & Services → Library**.
2. Search **Gmail API** → **Enable**.

### 2.3 Configure the consent screen (Google Auth Platform)
Go to **Google Auth Platform** (APIs & Services → OAuth consent screen).

**Branding**
- App name: `Absence Demo`
- User support email and developer contact email: your email

These appear on the consent screen, so users know who is asking for access.

**Audience**
- **Internal**: only accounts in your Workspace organization can sign in. No Google review and no test-user list are needed. *Recommended for TDTU accounts.*
- **External + Testing**: any Google account, but only the **test users** you add here. Add both the worker and manager emails.

**Data Access** → **Add or remove scopes**
- Tick `openid` and `.../auth/userinfo.email`.
- Under **Manually add scopes**, paste `https://mail.google.com/` → **Add to table** → **Update** → **Save**.

`https://mail.google.com/` is the only scope Gmail SMTP accepts for OAuth login. Google classifies it as **restricted**.

### 2.4 Create the OAuth client
1. **Clients → Create client**.
2. Application type: **Web application**.
3. Name: anything (e.g. `absence-demo-web`).
4. **Authorized JavaScript origins**: leave empty.
5. **Authorized redirect URIs** → add **exactly**:
   ```
   http://localhost:8002/auth/callback
   ```
6. Click **Create**, then copy the **Client ID** and **Client Secret**.

The Client Secret is private. Never commit it or share it. If it leaks, open the client → **Add secret** → update `.env` → disable and delete the old secret.

---

## 3. Set up the project in the code editor

Open the project folder in your editor (e.g. VS Code) and use its terminal.

### 3.1 Create a virtual environment and install packages
```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.2 Create the `.env` file
```bash
cp .env.example .env
```
Open `.env` and fill it in:
```
GOOGLE_CLIENT_ID=<Client ID from step 2.4>
GOOGLE_CLIENT_SECRET=<Client Secret from step 2.4>
SESSION_SECRET=<random string, see below>
BASE_URL=http://localhost:8002
MANAGER_EMAILS=manager@student.tdtu.edu.vn
```
- **`SESSION_SECRET`** signs the login cookie. Generate one with:
  ```bash
  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- **`BASE_URL`** must use the same host and port as the redirect URI registered in step 2.4.
- **`MANAGER_EMAILS`** is a comma-separated list, **lowercase, no spaces**. These accounts get the manager home page.

`.env` is listed in `.gitignore`. Keep it that way.

### 3.3 Run the app
```bash
uvicorn app.main:app --port 8002
```
Open **http://localhost:8002**. Use `localhost`, not `127.0.0.1`: the redirect URI must match exactly.

Avoid `--reload` while demoing. Every code change restarts the server, and in-memory data is lost (see Constraints).

---

## 4. Running the demo

| Step | Browser | What to do | What happens |
|---|---|---|---|
| 1 | A (worker) | Open `localhost:8002` → **Sign in with Google** → choose the worker account → **Allow** | OAuth sign-in; the app now holds the worker's token |
| 2 | A | Fill in the leave form (manager's email, dates, reason) → **Send via Gmail** | The request email is sent **from the worker's Gmail** |
| 3 | B (manager) | Open the manager's Gmail | The email arrived, with **Yes / No** buttons |
| 4 | B | Click **Yes** (or **No**) → sign in with the manager account if asked | The decision is recorded and the reply is sent **from the manager's Gmail** |
| 5 | B | Open `localhost:8002` | Manager page: requests still waiting (now empty) |
| 6 | A | Open the worker's Gmail | The "Re: Absence request…" reply sits in the **same thread** |

---

## 5. Project structure

```
app/
├── config.py      reads .env (client ID/secret, session secret, base URL, manager list)
├── oauth.py       OAuth 2.0: build the Google login URL, exchange code for tokens, refresh tokens
├── mailer.py      Gmail SMTP: STARTTLS + AUTH XOAUTH2, threading headers
├── db.py          in-memory storage (Python dictionaries) for users and requests
├── main.py        FastAPI routes: /, /login, /auth/callback, /logout, /requests, /requests/{id}/decide
└── templates/     Jinja2 pages (base, login, home, manager, decided) and HTML emails
                   (email_request.html with the Yes/No buttons, email_reply.html)
```

**Authorization Code flow in the code:**

| OAuth step | Code |
|---|---|
| Redirect to Google | `/login` → `oauth.authorization_url()` |
| User signs in and consents | Google's page (no app code) |
| Code returned | `/auth/callback` (checks `state`) |
| Code + secret → tokens + email | `oauth.exchange_code()` |
| Token used for SMTP | `mailer.send_mail()` → `AUTH XOAUTH2` |
| Token refresh (~1 hour) | `oauth.access_token_for()` |

---

## 6. Constraints and limitations

This is a **teaching demo**, not production software.

**Storage and runtime**
- **In-memory storage only.** Users, tokens and requests live in Python dictionaries, so stopping or restarting the server (including `--reload`) erases everything. Users must sign in again, and Yes/No links in old emails return 404.
- **Single process only.** Running multiple workers (`--workers N`) breaks the app, because each process has its own memory.
- **Runs on `localhost` over HTTP.** The Yes/No links point to `localhost:8002`, so they only work on the machine running the app. Using another device or a real deployment needs a public **HTTPS** URL, a matching `BASE_URL`, and that URL registered as a redirect URI.

**Google and Gmail**
- **Broad Gmail scope.** SMTP requires `https://mail.google.com/` (read, send and delete all mail). The app only sends, but the token technically allows more. The Gmail API with `gmail.send` would be narrower.
- **No public release without Google review.** `https://mail.google.com/` is a *restricted* scope. Outside Internal or Testing mode, Google requires app verification and a security assessment.
- **Testing mode tokens expire.** With External + Testing, refresh tokens expire after **7 days**, so users must sign in again.
- **Organization policies.** A Workspace admin may block third-party apps or restricted scopes. Then sign-in shows "Access blocked".
- **Gmail sending limits.** About 500 recipients/day for personal accounts and about 2,000 for Workspace. Not suitable for bulk or marketing email.

**Application behaviour**
- **Manager list is strict.** `MANAGER_EMAILS` is split on commas only, so entries must be lowercase with no spaces.
- **The recipient isn't checked against the manager list.** A worker can send a request to any address. That person can answer through the email buttons but won't get the manager page.
- **Decisions are final.** No cancel, edit or undo. Only the first Yes/No click counts.
- **Minimal validation.** Dates aren't validated (an end date before the start date is accepted).
- **Minimal error handling.** Google or SMTP errors appear as a raw error page. If sending fails after a request is created, the request stays PENDING with no email sent.
- **HTML-only emails.** No plain-text alternative part.
- **No CSRF token on the form.** The `SameSite=Lax` session cookie mitigates this; a production app should add one.

**Security measures that *are* included:** the OAuth `state` check, a signed session cookie (`SESSION_SECRET`), a random token in each Yes/No link compared with `compare_digest`, a check that the signed-in user is the intended manager, STARTTLS before sending the token, and Jinja2 HTML auto-escaping.
