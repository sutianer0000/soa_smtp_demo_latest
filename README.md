# Gmail SMTP + OAuth 2.0: Absence Request Demo

A small FastAPI web app that helps automate the process of sending email for absense

**workflow**
- A **worker** signs in with Google and submits a leave request.
- The app emails the **manager** from the worker's Gmail, through Gmail SMTP.
- The manager clicks **Yes** or **No** in the email.
- The app replies to the worker **from the manager's Gmail**, in the same email thread(reply).

Login to Gmail SMTP uses an **OAuth 2.0 access token** (SASL `XOAUTH2`)

---

## 1. Requirements

- Python **3.10+**
- Two Google accounts for the demo: one **worker**, one **manager**. See **Accounts** in [Constraints](#6-constraints-and-limitations).

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
source .venv/bin/activate      

# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3.2 Create the `.env` file or just rename it to .env
```bash
cp .env.example .env
```
Open `.env` and fill it in:
```
GOOGLE_CLIENT_ID=<Client ID from step 2.4>
GOOGLE_CLIENT_SECRET=<Client Secret from step 2.4>
SESSION_SECRET=<random string, see below>
BASE_URL=http://localhost:8002
MANAGER_EMAILS=manager@student.tdtu.edu.vn (choose 1 as the manager's email)
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

The whole demo runs in **one browser**. Do the worker's part (A) first, then sign out of the app and continue as the manager (B).

| Step | Account | What to do | What happens |
|---|---|---|---|
| 1 | A (worker) | Open `localhost:8002` → **Sign in with Google** → choose the worker account → **Allow** | OAuth sign-in; the app now holds the worker's token |
| 2 | A | Fill in the leave form (manager's email, dates, reason) → **Send via Gmail** | The request email is sent **from the worker's Gmail** |
| 3 | – | Click **Sign out** in the app | The app no longer treats the browser as A |
| 4 | B (manager) | Open the manager's Gmail mailbox and the request email | The email arrived, with **Yes / No** buttons |
| 5 | B | Click **Yes** (or **No**) → **Sign in with Google** as the manager → **Allow** | The decision is recorded and the reply is sent **from the manager's Gmail** |
| 6 | B | Open `localhost:8002` | Manager page: requests still waiting (now empty) |
| 7 | A | Switch to the worker's Gmail mailbox | The "Re: Absence request…" reply sits in the **same thread** |

**Gmail mailboxes vs. app sign-in:** both Gmail accounts can stay signed in to Google in the same browser, and you can switch between the two mailboxes (profile picture → choose account). Every email displays normally in either mailbox. But the **Yes / No buttons only work when you are signed in to the app as that manager**. If the app session belongs to the worker, or to nobody, clicking a button first sends you to **Sign in with Google**, where you must choose the manager account.

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

This is a **demo**, not production software.

**Accounts**
- **Built for two internal TDTU accounts.** The demo uses the **Internal** audience: only the two `@student.tdtu.edu.vn` accounts (worker and manager) in the TDTU organization can sign in.
- **External accounts need test users.** The app can be reconfigured with the **External** audience, but then every Gmail account that signs in must be listed under **Test users**.
- **Student email is TDTU-only.** `@student.tdtu.edu.vn` accounts cannot send to or receive from external addresses (e.g. `@gmail.com`), so the worker and manager must both be TDTU accounts, or both be external accounts.

**Storage and runtime**
- **In-memory storage only.** Users, tokens and requests live in Python dictionaries, so stopping or restarting the server (including `--reload`) erases everything. Users must sign in again, and Yes/No links in old emails return 404.
- **Single process only.** Running multiple workers (`--workers N`) breaks the app, because each process has its own memory.
- **Runs on `localhost` over HTTP.** The Yes/No links point to `localhost:8002`, so they only work on the machine running the app. Using another device or a real deployment needs a public **HTTPS** URL, a matching `BASE_URL`, and that URL registered as a redirect URI.
