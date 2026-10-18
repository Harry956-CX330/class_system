from auth import create_access_token
from auth import get_current_user
from auth import get_password_hash
from auth import require_admin
from auth import verify_password
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from qr_db import CheckinRecord, CheckinTask, QrSessionLocal
from fastapi import APIRouter, Request, Response
from security import login_accounts
from auth import SECRET_KEY
import hmac
import hashlib
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from fastapi import status
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.responses import StreamingResponse
from models import CounselorInfo
from models import User
from schemas import ClassCommitteeResponse
from schemas import ClassCommitteeUpdate
from schemas import CounselorInfoResponse
from schemas import CounselorInfoUpdate
from schemas import LoginRequest
from schemas import LoginResponse
from schemas import PasswordChange
from schemas import UserCreate
from schemas import UserImportItem
from schemas import UserResponse
from schemas import UserSelfUpdate
from schemas import UserUpdate
from services.files import build_zip_response, safe_upload_path, save_upload, read_small_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config, _send_qq_msg
from services.utils import HAS_OPENPYXL
from services.utils import decode_csv_content
from services.utils import openpyxl
from services.utils import user_to_dict
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
import csv
import io

router = APIRouter(tags=["users"])
_DUMMY_HASH = get_password_hash("not-a-real-account-password")


@router.post("/api/login", response_model=LoginResponse)
def login(req: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db, scope="function")):
    key = hmac.new(SECRET_KEY.encode(), req.username.strip().lower().encode(), hashlib.sha256).digest()
    if not login_accounts.allow(key, 8, 300):
        raise HTTPException(429, "该账号登录尝试过多，请五分钟后再试", headers={"Retry-After": "300"})
    name = req.username.strip()
    matches = db.query(User).filter(or_(User.username == name, User.student_id == name, User.real_name == name)).all()
    user = matches[0] if len(matches) == 1 else None
    if user and not login_accounts.allow(("login-user", user.id), 16, 300):
        raise HTTPException(429, "该账号登录尝试过多，请五分钟后再试")
    valid = verify_password(req.password, user.hashed_password if user else _DUMMY_HASH)
    if not user or not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(data={"user_id": user.id})
    response.set_cookie("media_session", token, max_age=3600, httponly=True, secure=request.url.scheme == "https", samesite="strict", path="/static")
    return LoginResponse(access_token=token, user=user_to_dict(user))



@router.get("/api/users", response_model=list[UserResponse])
def list_users(role: str = Query(None), db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.all()



@router.get("/api/users/profile", response_model=UserResponse)
def get_my_profile(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    return current_user



@router.post("/api/users", response_model=UserResponse)
def create_user(data: UserCreate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    if (data.role == "admin" or data.is_class_leader) and current_user.role != "admin":
        raise HTTPException(403,"仅系统管理员可设置管理权限")
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    user = User(
        username=data.username, hashed_password=get_password_hash(data.password),
        role=data.role, real_name=data.real_name, student_id=data.student_id,
        political_status=data.political_status, email=data.email,
        is_class_leader=data.is_class_leader,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user



@router.get("/api/class-committee", response_model=list[ClassCommitteeResponse])
def get_class_committee(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    """获取班委通讯录（仅显示已勾选展示的班委，按排序值升序）"""
    leaders = db.query(User).filter(User.is_class_leader == True, User.show_in_committee == True).order_by(User.sort_order, User.id).all()
    return [ClassCommitteeResponse(
        id=u.id, real_name=u.real_name,
        class_position=u.class_position or "",
        phone=u.phone or "",
        qq_number=u.qq_number or "",
        dorm=u.dorm or "",
        show_in_committee=u.show_in_committee or False,
        sort_order=u.sort_order or 0,
    ) for u in leaders]



@router.get("/api/class-committee/all", response_model=list[ClassCommitteeResponse])
def get_all_class_leaders(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """获取所有班委（管理端用，不限制展示状态，按排序值升序）"""
    leaders = db.query(User).filter(User.is_class_leader == True).order_by(User.sort_order, User.id).all()
    return [ClassCommitteeResponse(
        id=u.id, real_name=u.real_name,
        class_position=u.class_position or "",
        phone=u.phone or "",
        qq_number=u.qq_number or "",
        dorm=u.dorm or "",
        sort_order=u.sort_order or 0,
    ) for u in leaders]



@router.put("/api/class-committee/{user_id}", response_model=ClassCommitteeResponse)
def update_class_committee(user_id: int, data: ClassCommitteeUpdate, db: Session = Depends(get_db, scope="function"),
                           current_user: User = Depends(require_admin)):
    """管理员更新班委职位信息（含排序）"""
    user = db.query(User).filter(User.id == user_id, User.is_class_leader == True).first()
    if not user: raise HTTPException(status_code=404, detail="用户不存在或不是班委")
    if data.class_position is not None: user.class_position = data.class_position
    if data.phone is not None: user.phone = data.phone
    if data.qq_number is not None: user.qq_number = data.qq_number
    if data.dorm is not None: user.dorm = data.dorm
    if data.show_in_committee is not None: user.show_in_committee = data.show_in_committee
    if data.sort_order is not None: user.sort_order = data.sort_order
    db.commit()
    db.refresh(user)
    return ClassCommitteeResponse(
        id=user.id, real_name=user.real_name,
        class_position=user.class_position or "",
        phone=user.phone or "",
        qq_number=user.qq_number or "",
        dorm=user.dorm or "",
        sort_order=user.sort_order or 0,
    )



@router.get("/api/counselor", response_model=CounselorInfoResponse)
def get_counselor_info(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    """获取辅导员信息"""
    info = db.query(CounselorInfo).first()
    if not info:
        return {"id":0,"name":"","office":"","phone":"","qq_number":""}
    return info



@router.put("/api/counselor", response_model=CounselorInfoResponse)
def update_counselor_info(data: CounselorInfoUpdate, db: Session = Depends(get_db, scope="function"),
                          current_user: User = Depends(require_admin)):
    """更新辅导员信息"""
    info = db.query(CounselorInfo).first()
    if not info:
        info = CounselorInfo()
        db.add(info)
    if data.name is not None: info.name = data.name
    if data.office is not None: info.office = data.office
    if data.phone is not None: info.phone = data.phone
    if data.qq_number is not None: info.qq_number = data.qq_number
    db.commit()
    db.refresh(info)
    return info



@router.post("/api/users/import")
def import_users(items: list[UserImportItem], db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    created = 0
    errors = []
    for item in items:
        existing = db.query(User).filter(User.username == item.username).first()
        if existing:
            errors.append(f"用户 {item.username} 已存在")
            continue
        user = User(
            username=item.username, hashed_password=get_password_hash(item.password),
            role="student", real_name=item.real_name, student_id=item.student_id,
            political_status=item.political_status, email=item.email,
        )
        db.add(user)
        created += 1
    db.commit()
    return {"created": created, "errors": errors}



@router.post("/api/users/import-file")
async def import_users_file(file: UploadFile = File(...), db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    created = 0
    errors = []
    content = await read_small_upload(file, MAX_IMPORT_BYTES)

    filename = file.filename or ""
    if filename.lower().endswith(".csv"):
        text = decode_csv_content(content)
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                username = row.get("username") or row.get("学号") or ""
                real_name = row.get("real_name") or row.get("姓名") or ""
                student_id = row.get("student_id") or row.get("学号") or username
                political_status = row.get("political_status") or row.get("政治面貌") or ""
                email = row.get("email") or row.get("邮箱") or ""
                qq_number = row.get("qq_number") or row.get("QQ号") or ""
                password = row.get("password") or row.get("密码") or "123456"
                if not username:
                    continue
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    errors.append(f"用户 {username} 已存在")
                    continue
                user = User(username=username, hashed_password=get_password_hash(password),
                            role="student", real_name=real_name, student_id=student_id,
                            political_status=political_status, email=email, qq_number=qq_number)
                db.add(user)
                created += 1
            except Exception as e:
                errors.append(str(e))
    elif filename.lower().endswith((".xlsx", ".xls")):
        if not HAS_OPENPYXL:
            raise HTTPException(status_code=500, detail="服务器未安装 openpyxl")
        wb = openpyxl.load_workbook(io.BytesIO(content))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        for row in ws.iter_rows(min_row=2, values_only=True):
            row_dict = dict(zip(headers, row))
            try:
                username = row_dict.get("username") or row_dict.get("学号") or ""
                real_name = row_dict.get("real_name") or row_dict.get("姓名") or ""
                student_id = row_dict.get("student_id") or row_dict.get("学号") or username
                political_status = row_dict.get("political_status") or row_dict.get("政治面貌") or ""
                email = row_dict.get("email") or row_dict.get("邮箱") or ""
                qq_number = row_dict.get("qq_number") or row_dict.get("QQ号") or ""
                password = row_dict.get("password") or row_dict.get("密码") or "123456"
                if not username:
                    continue
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    errors.append(f"用户 {username} 已存在")
                    continue
                user = User(username=username, hashed_password=get_password_hash(str(password)),
                            role="student", real_name=str(real_name), student_id=str(student_id),
                            political_status=str(political_status), email=str(email), qq_number=str(qq_number))
                db.add(user)
                created += 1
            except Exception as e:
                errors.append(str(e))
    else:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls / .csv 格式")

    db.commit()
    return {"created": created, "errors": errors}



@router.get("/api/users/template")
def download_user_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["username", "real_name", "student_id", "political_status", "email", "qq_number", "password"])
    writer.writerow(["2024001", "张三", "2024001", "团员", "zhangsan@qq.com", "123456789", "123456"])
    writer.writerow(["2024002", "李四", "2024002", "群众", "lisi@qq.com", "987654321", "123456"])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=user_template.csv"})



@router.put("/api/users/me")
def update_self(data: UserSelfUpdate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    if data.real_name is not None: current_user.real_name = data.real_name
    if data.political_status is not None: current_user.political_status = data.political_status
    if data.email is not None: current_user.email = data.email
    if data.qq_number is not None: current_user.qq_number = data.qq_number
    db.commit()
    db.refresh(current_user)
    return user_to_dict(current_user)



@router.put("/api/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    if data.real_name is not None: user.real_name = data.real_name
    if data.student_id is not None: user.student_id = data.student_id
    if data.political_status is not None: user.political_status = data.political_status
    if data.email is not None: user.email = data.email
    if data.qq_number is not None: user.qq_number = data.qq_number
    if data.phone is not None: user.phone = data.phone
    if data.dorm is not None: user.dorm = data.dorm
    if data.class_position is not None: user.class_position = data.class_position
    if data.show_in_committee is not None: user.show_in_committee = data.show_in_committee
    if data.is_class_leader is not None:
        if current_user.role != "admin":
            raise HTTPException(403,"仅系统管理员可调整班委权限")
        user.is_class_leader = data.is_class_leader
    if data.is_dorm_leader is not None: user.is_dorm_leader = data.is_dorm_leader
    db.commit()
    db.refresh(user)
    return user



@router.delete("/api/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="用户不存在")
    if user.role == "admin": raise HTTPException(status_code=400, detail="不能删除管理员账号")
    # 删除账号时同步清理独立签到库，避免主库 ID 被复用后旧签到记录错挂到新账号。
    qr = QrSessionLocal()
    try:
        qr.query(CheckinRecord).filter(CheckinRecord.student_id == user_id).delete()
        qr.query(CheckinTask).filter(CheckinTask.author_id == user_id).update({CheckinTask.author_id: None})
        qr.commit()
    finally:
        qr.close()
    db.delete(user)
    db.commit()
    return {"message": "删除成功"}



@router.put("/api/users/me/password")
def change_password(data: PasswordChange, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(get_current_user)):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")
    if len(data.new_password) < 8 or len(data.new_password.encode("utf-8")) > 72:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码至少 8 位，且 UTF-8 编码不能超过 72 字节")
    current_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "密码修改成功"}

