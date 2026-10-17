from models import User

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    HAS_OPENPYXL = False


def decode_csv_content(content: bytes) -> str:
    """自动检测编码并解码 CSV 内容，兼容 UTF-8 和 GBK"""
    for encoding in ("utf-8-sig", "gbk", "gb2312", "latin-1"):
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError("无法识别文件编码，请使用 UTF-8 或 GBK 编码保存文件")



def user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "real_name": user.real_name,
        "student_id": user.student_id,
        "political_status": user.political_status,
        "email": user.email,
        "qq_number": user.qq_number,
        "is_class_leader": user.is_class_leader,
    }

