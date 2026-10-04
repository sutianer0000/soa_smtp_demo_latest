
#assign data from .evn to variables
import os

from dotenv import load_dotenv

load_dotenv()

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
SESSION_SECRET = os.environ["SESSION_SECRET"]
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")

# Must match the "Authorized redirect URI" registered on the OAuth client exactly.
REDIRECT_URI = f"{BASE_URL}/auth/callback" #assign the redirect uri to a variable

# Comma-separated list of manager emails; everyone else is treated as a worker.
MANAGER_EMAILS = os.environ.get("MANAGER_EMAILS", "").split(",")
