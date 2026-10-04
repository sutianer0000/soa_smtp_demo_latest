"""In-memory storage for the demo: everything is lost when the server stops or reloads."""
from itertools import count

users = {}              # email -> {"refresh_token", "access_token", "expires_at"}
absence_requests = {}   # id    -> {"id", "worker_email", "manager_email", "start_date", "end_date",
                        #           "reason", "status", "token", "message_id"}
_next_id = count(1)


# --- users -------------------------------------------------------------------

def save_user(email, refresh_token, access_token, expires_at):
    user = users.setdefault(email, {"refresh_token": None})
    # Google only returns a refresh_token on consent, so keep the old one if none is given.
    if refresh_token:
        user["refresh_token"] = refresh_token
    user["access_token"] = access_token
    user["expires_at"] = expires_at


def get_user(email):
    return users.get(email)


# --- requests ----------------------------------------------------------------

def create_request(worker_email, manager_email, start_date, end_date, reason, token):
    req_id = next(_next_id)
    absence_requests[req_id] = {
        "id": req_id,
        "worker_email": worker_email,
        "manager_email": manager_email,
        "start_date": start_date,
        "end_date": end_date,
        "reason": reason,
        "status": "PENDING",
        "token": token,
        "message_id": None,
    }
    return req_id


def get_request(req_id):
    return absence_requests.get(req_id)


def set_message_id(req_id, message_id):
    absence_requests[req_id]["message_id"] = message_id


def set_status(req_id, status):
    absence_requests[req_id]["status"] = status


def requests_from(worker_email):
    return [r for r in reversed(absence_requests.values()) if r["worker_email"] == worker_email]


def requests_to(manager_email):
    return [r for r in reversed(absence_requests.values()) if r["manager_email"] == manager_email]
