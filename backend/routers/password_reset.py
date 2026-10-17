"""Administrator-issued, single-use reset codes, without schema migrations."""
import hashlib
import hmac
import secrets
import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from auth import SECRET_KEY, get_password_hash
from database import get_db
from models import User
from routers.branding import system_admin
from security import login_accounts
from services.private_settings import settings_lock, read_settings, write_settings

router = APIRouter(tags=["password reset"])
def digest(user_id, code):
    return hmac.new(SECRET_KEY.encode(),f"reset:{user_id}:{code}".encode(),hashlib.sha256).hexdigest()

class ResetRequest(BaseModel):
    username: str = Field(min_length=1,max_length=50)
    code: str = Field(pattern=r"^\d{8}$")
    password: str = Field(min_length=8,max_length=72)

@router.post("/api/users/{user_id}/reset-code")
def issue_code(user_id: int, admin=Depends(system_admin), db: Session=Depends(get_db,scope="function")):
    if not db.get(User,user_id):
        raise HTTPException(404,"用户不存在")
    if not login_accounts.allow(("issue-reset",admin.id,user_id),5,600):
        raise HTTPException(429,"请稍后再生成验证码")
    code = f"{secrets.randbelow(100000000):08d}"
    with settings_lock:
        records = read_settings("password-resets.json",{})
        records = {key:value for key,value in records.items() if value["expires"] > time.time()}
        records[str(user_id)] = {"hash":digest(user_id,code),"expires":time.time()+600,"attempts":0}
        write_settings("password-resets.json",records)
    return {"code":code,"expires_in":600}

@router.post("/api/password-reset")
def reset_password(data: ResetRequest, db: Session=Depends(get_db,scope="function")):
    name = data.username.strip()
    if not login_accounts.allow(("reset",hashlib.sha256(name.encode()).digest()),8,600):
        raise HTTPException(429,"尝试过多，请十分钟后再试")
    users = db.query(User).filter(or_(User.username==name,User.student_id==name,User.real_name==name)).all()
    user = users[0] if len(users)==1 else None
    with settings_lock:
        records = read_settings("password-resets.json",{})
        key = str(user.id) if user else ""
        record = records.get(key)
        valid = record and record["expires"]>time.time() and record["attempts"]<5
        if record:
            record["attempts"] += 1
            write_settings("password-resets.json",records)
        if not valid or not hmac.compare_digest(record["hash"],digest(user.id,data.code)):
            raise HTTPException(400,"账号或验证码不正确，或验证码已过期；重名请使用学号")
        if len(data.password.encode())>72:
            raise HTTPException(422,"密码不能超过 72 字节")
        user.hashed_password = get_password_hash(data.password)
        revocations = read_settings("password-revocations.json", {})
        revocations[str(user.id)] = time.time()
        write_settings("password-revocations.json", revocations)
        db.commit()
        records.pop(key,None)
        write_settings("password-resets.json",records)
    return {"message":"密码已重置，请使用新密码登录"}
