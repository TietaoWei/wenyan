from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models import init_db, create_user, get_user_by_username, init_progress
from auth import hash_password, verify_password, create_token
from api import router as api_router

app = FastAPI(title="知文阁 API")
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/api/register")
def register(body: dict):
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return {"ok": False, "error": "用户名和密码不能为空"}
    if len(username) > 50 or len(password) > 100:
        return {"ok": False, "error": "用户名或密码过长"}
    if get_user_by_username(username):
        return {"ok": False, "error": "该用户名已被注册"}
    from datetime import datetime, timezone
    pw_hash = hash_password(password)
    user_id = create_user(username, pw_hash, datetime.now(timezone.utc).isoformat())
    init_progress(user_id)
    token = create_token(user_id, username)
    return {"ok": True, "token": token, "username": username}


@app.post("/api/login")
def login(body: dict):
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not username or not password:
        return {"ok": False, "error": "用户名和密码不能为空"}
    user = get_user_by_username(username)
    if not user:
        return {"ok": False, "error": "用户不存在"}
    if not verify_password(password, user["password_hash"]):
        return {"ok": False, "error": "密码错误"}
    token = create_token(user["id"], username)
    return {"ok": True, "token": token, "username": username}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
