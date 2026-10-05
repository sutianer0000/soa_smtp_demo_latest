# Gmail SMTP + OAuth 2.0: Absence Request Demo

A small FastAPI app where a **worker** sends a leave request from their own Gmail, and the **manager** approves or rejects it with **Yes / No** buttons in the email. The reply goes back in the same thread.

**Why:** the app sends email **as the user** through Gmail SMTP **without ever knowing their password**. The user approves on Google's page, and the app logs in to SMTP with a limited **OAuth 2.0 token** (`XOAUTH2`).

---

## 1. Get the code

Either:
- **Git:** `git clone https://github.com/sutianer0000/soa_smtp_demo_latest.git`
- **ZIP:** open <https://github.com/sutianer0000/soa_smtp_demo_latest> → **Code** → **Download ZIP**, then unzip it.

## 2. Google Cloud setup

At <https://console.cloud.google.com>:
1. **New Project** (location: your organization, e.g. `tdtu.edu.vn`).
2. **APIs & Services → Library → Gmail API → Enable**.
3. **Google Auth Platform:**
   - **Branding:** app name and support email.
   - **Audience:** **Internal**.
   - **Data Access:** add `openid` and `.../auth/userinfo.email`, and manually add `https://mail.google.com/`. Save.
4. **Clients → Create client:**
   - type **Web application**,
   - redirect URI `http://localhost:8002/auth/callback`,
   - Create, then copy the **Client ID** and **Client Secret**.

## 3. Run

```bash
cd soa_smtp_demo_latest          # ZIP download: cd soa_smtp_demo_latest-2.0
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # or rename .env.example to .env
```

Fill in `.env`:
```
GOOGLE_CLIENT_ID=<Client ID>
GOOGLE_CLIENT_SECRET=<Client Secret>
SESSION_SECRET=<output of: python3 -c "import secrets; print(secrets.token_urlsafe(32))">
BASE_URL=http://localhost:8002
MANAGER_EMAILS=manager@student.tdtu.edu.vn
```

Start the server and open **http://localhost:8002**:
```bash
uvicorn app.main:app --port 8002
```

## 4. Try it

1. **Worker:** Sign in with Google, fill in the form, then **Send via Gmail**.
2. **Sign out** in the app.
3. **Manager:** open the email in Gmail and click **Yes** or **No**. The app asks you to sign in as the manager.
4. **Worker:** the reply appears in the same Gmail thread.

## Notes

- **Accounts:** built for two **@student.tdtu.edu.vn** accounts (Internal audience). With an External audience, every account must be added as a **test user**. Student emails can't send to or receive from external addresses.
- **Data is in memory:** restarting the server clears everything, so don't use `--reload` while demoing.
- **Localhost only:** the email buttons work only on the machine running the app.
- **Keep secrets private:** never commit or share `.env` or the Client Secret.
