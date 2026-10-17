from sqlalchemy.orm import Session
from models import User
from auth import get_password_hash


def init_db(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin_user = User(
            username="admin",
            hashed_password=get_password_hash("123456"),
            role="admin",
            real_name="管理员",
            student_id="admin",
        )
        db.add(admin_user)
        db.commit()
