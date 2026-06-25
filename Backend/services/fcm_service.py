import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

_initialized = False

def _init_fcm():
    global _initialized
    if not _initialized:
        cred_json = os.getenv("FCM_CREDENTIALS_JSON")
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
            firebase_admin.initialize_app(cred)
            _initialized = True

def send_single_fcm(token: str, title: str, body: str, data: dict = {}):
    if not token:
        return
    _init_fcm()
    if not _initialized: return
    msg = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        data=data,
        token=token
    )
    try:
        messaging.send(msg)
    except Exception:
        pass

def send_batch_fcm(tokens: list[str], title: str, body: str, data: dict = {}, db=None):
    valid_tokens = [t for t in tokens if t]
    if not valid_tokens:
        return
    _init_fcm()
    if not _initialized: return
    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            token=token
        )
        for token in valid_tokens
    ]
    try:
        response = messaging.send_each(messages)
        if db:
            for i, result in enumerate(response.responses):
                if not result.success and "UNREGISTERED" in str(result.exception):
                    from models.user import User
                    db.query(User).filter_by(fcm_token=valid_tokens[i]).update({"fcm_token": None})
            db.commit()
    except Exception:
        pass
