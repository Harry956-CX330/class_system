from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from database import Base

BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now():
    """返回当前北京时间（naive datetime，适配 SQLite）"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="student")
    is_class_leader = Column(Boolean, nullable=False, default=False)
    real_name = Column(String(50), default="")
    student_id = Column(String(50), unique=True, default="")
    political_status = Column(String(50), default="")
    email = Column(String(100), default="")
    qq_number = Column(String(20), default="")
    phone = Column(String(20), default="")
    dorm = Column(String(50), default="")
    class_position = Column(String(50), default="")
    show_in_committee = Column(Boolean, nullable=False, default=False)
    sort_order = Column(Integer, nullable=False, default=0)  # 班委展示排序，越小越靠前
    is_dorm_leader = Column(Boolean, nullable=False, default=False)  # 宿舍长
    created_at = Column(DateTime, default=beijing_now)

    notices = relationship("Notice", back_populates="author")
    certificates = relationship("Certificate", back_populates="student")
    grades = relationship("Grade", back_populates="student")
    social_practices = relationship("SocialPractice", back_populates="student")
    file_submissions = relationship("FileSubmission", back_populates="student")
    survey_responses = relationship("SurveyResponse", back_populates="student")
    class_meetings = relationship("ClassMeeting", back_populates="author")
    resource_files = relationship("ResourceFile", back_populates="uploader")
    group_projects = relationship("GroupProject", back_populates="admin")
    group_assignments = relationship("GroupAssignment", back_populates="student")
    activities = relationship("Activity", back_populates="author")
    activity_participants = relationship("ActivityParticipant", back_populates="student")


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
    is_urgent = Column(Boolean, nullable=False, default=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User", back_populates="notices")


class CounselorInfo(Base):
    """辅导员信息（单行记录）"""
    __tablename__ = "counselor_info"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), default="")
    office = Column(String(200), default="")
    phone = Column(String(20), default="")
    qq_number = Column(String(20), default="")
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    award_name = Column(String(200), nullable=False)
    award_level = Column(String(50), nullable=False, default="校级")
    award_date = Column(DateTime, default=beijing_now)
    image_path = Column(String(500), default="")
    created_at = Column(DateTime, default=beijing_now)

    student = relationship("User", back_populates="certificates")


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Float, nullable=False)
    gpa = Column(Float, nullable=False)
    semester = Column(String(50), nullable=False)
    academic_year = Column(String(50), nullable=False)
    class_rank = Column(Integer, default=0)
    total_students = Column(Integer, default=0)
    created_at = Column(DateTime, default=beijing_now)

    student = relationship("User", back_populates="grades")


class GradeChangeRequest(Base):
    """成绩修改申请（学生提交 → 管理员审批）"""
    __tablename__ = "grade_change_requests"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)  # 修改已有成绩时为 grade_id，新增时为 None
    proposed_score = Column(Float, nullable=False, default=0)
    proposed_gpa = Column(Float, nullable=False, default=0)
    proposed_semester = Column(String(50), nullable=False, default="")
    proposed_academic_year = Column(String(50), nullable=False, default="")
    proposed_class_rank = Column(Integer, default=0)
    proposed_total_students = Column(Integer, default=0)
    status = Column(String(20), nullable=False, default="pending")  # pending / approved / rejected
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    admin_comment = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)

    student = relationship("User", foreign_keys=[student_id])
    admin = relationship("User", foreign_keys=[admin_id])
    grade = relationship("Grade")


class SocialPractice(Base):
    __tablename__ = "social_practices"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_name = Column(String(200), nullable=False)
    role = Column(String(100), default="")
    description = Column(Text, default="")
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    certificate_image = Column(String(500), default="")
    created_at = Column(DateTime, default=beijing_now)

    student = relationship("User", back_populates="social_practices")


class FileTask(Base):
    __tablename__ = "file_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)
    deadline = Column(DateTime, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    naming_pattern = Column(String(200), default="{name}_{sid}")
    group_project_id = Column(Integer, ForeignKey("group_projects.id"), nullable=True)

    author = relationship("User")
    submissions = relationship("FileSubmission", back_populates="task", cascade="all, delete-orphan")
    group_project = relationship("GroupProject")


class FileSubmission(Base):
    __tablename__ = "file_submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("file_tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    file_path = Column(String(500), default="")
    original_name = Column(String(200), default="")
    submitted_at = Column(DateTime, default=beijing_now)

    task = relationship("FileTask", back_populates="submissions")
    student = relationship("User", back_populates="file_submissions")


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    deadline = Column(DateTime, nullable=True)
    is_anonymous = Column(Boolean, default=False)
    show_results = Column(Boolean, default=True)
    allow_multiple = Column(Boolean, default=False)
    created_at = Column(DateTime, default=beijing_now)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    author = relationship("User")
    questions = relationship("SurveyQuestion", back_populates="survey", cascade="all, delete-orphan")


class SurveyQuestion(Base):
    __tablename__ = "survey_questions"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False)
    question_text = Column(String(500), nullable=False)
    description = Column(Text, default="")
    question_type = Column(String(20), nullable=False, default="text")
    options = Column(Text, default="")

    survey = relationship("Survey", back_populates="questions")
    responses = relationship("SurveyResponse", back_populates="question", cascade="all, delete-orphan")


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("survey_questions.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_text = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)

    question = relationship("SurveyQuestion", back_populates="responses")
    student = relationship("User", back_populates="survey_responses")


class ClassMeeting(Base):
    __tablename__ = "class_meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    meeting_date = Column(DateTime, nullable=False)
    location = Column(String(200), default="")
    description = Column(Text, default="")
    status = Column(String(20), default="upcoming")
    created_at = Column(DateTime, default=beijing_now)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_leader_id = Column(Integer, nullable=True)  # 考勤班干
    host_leader_id = Column(Integer, nullable=True)        # 主持+写班会记录班干

    author = relationship("User", back_populates="class_meetings")
    record = relationship("ClassMeetingRecord", uselist=False, back_populates="meeting", cascade="all, delete-orphan")


class ClassMeetingRecord(Base):
    __tablename__ = "class_meeting_records"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("class_meetings.id"), nullable=False, unique=True)
    record_text = Column(Text, default="")
    images = Column(String(2000), default="[]")
    record_file = Column(String(300), default="")       # 班会记录文件（存储文件名）
    record_file_name = Column(String(300), default="")  # 记录文件原始名
    created_at = Column(DateTime, default=beijing_now)

    meeting = relationship("ClassMeeting", back_populates="record")


class ResourceCategory(Base):
    __tablename__ = "resource_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)

    files = relationship("ResourceFile", back_populates="category", cascade="all, delete-orphan")


class ResourceFile(Base):
    __tablename__ = "resource_files"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("resource_categories.id"), nullable=False)
    filename = Column(String(200), nullable=False)
    original_name = Column(String(300), default="")
    file_path = Column(String(500), default="")
    file_size = Column(Integer, default=0)
    file_type = Column(String(20), default="")
    visibility = Column(String(20), default="student")
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=beijing_now)

    category = relationship("ResourceCategory", back_populates="files")
    uploader = relationship("User", back_populates="resource_files")


class GroupProject(Base):
    __tablename__ = "group_projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    group_count = Column(Integer, nullable=False, default=4)
    members_per_group = Column(Integer, nullable=False, default=6)
    group_capacities = Column(Text, nullable=True)  # JSON: [6, 5, 7, 6] 每组容量，null表示统一容量
    group_names = Column(Text, nullable=True)  # JSON: {"1": "学霸组", "2": "勤奋组", ...} 自定义组名
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    admin = relationship("User", back_populates="group_projects")
    assignments = relationship("GroupAssignment", back_populates="project", cascade="all, delete-orphan")


class GroupAssignment(Base):
    __tablename__ = "group_assignments"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("group_projects.id"), nullable=False)
    group_number = Column(Integer, nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), default="member")
    created_at = Column(DateTime, default=beijing_now)

    project = relationship("GroupProject", back_populates="assignments")
    student = relationship("User", back_populates="group_assignments")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    location = Column(String(200), default="")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    qr_token = Column(String(100), default="")
    checkin_code = Column(String(4), default="0000")
    checkin_mode = Column(String(20), default="auto")  # auto=定时刷新, fixed=固定数字
    checkin_interval = Column(Integer, default=2)      # 签到码刷新间隔（秒），auto 模式生效
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=beijing_now)

    author = relationship("User", back_populates="activities")
    participants = relationship("ActivityParticipant", back_populates="activity", cascade="all, delete-orphan")


class ActivityParticipant(Base):
    __tablename__ = "activity_participants"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sign_status = Column(String(20), default="absent")
    sign_time = Column(DateTime, nullable=True)

    activity = relationship("Activity", back_populates="participants")
    student = relationship("User", back_populates="activity_participants")


class EmailHistory(Base):
    """邮件发送历史记录"""
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, index=True)
    recipient_email = Column(String(100), nullable=False)
    recipient_name = Column(String(50), default="")
    subject = Column(String(500), nullable=False)
    send_type = Column(String(20), nullable=False, default="test")  # notice / file_task / survey / test
    related_id = Column(Integer, nullable=True)  # 关联的业务ID（通知ID/任务ID/问卷ID）
    status = Column(String(10), nullable=False, default="sent")  # sent / failed
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)


class Textbook(Base):
    """教材"""
    __tablename__ = "textbooks"

    id = Column(Integer, primary_key=True, index=True)
    course_name = Column(String(200), nullable=False, default="")      # 课程名称
    name = Column(String(200), nullable=False)                         # 教材名称
    isbn = Column(String(50), default="")                              # ISBN
    publisher = Column(String(200), default="")                        # 出版社
    author = Column(String(200), default="")                           # 作者
    course_type = Column(String(20), nullable=False, default="必修")    # 必修 / 选修
    original_price = Column(Float, nullable=False, default=0.0)        # 单价
    discounted_price = Column(Float, nullable=False, default=0.0)      # 折后单价
    quantity = Column(Integer, nullable=False, default=0)              # （保留兼容旧库，前端不显示）
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class TextbookOrder(Base):
    """教材订购记录"""
    __tablename__ = "textbook_orders"

    id = Column(Integer, primary_key=True, index=True)
    textbook_id = Column(Integer, ForeignKey("textbooks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=beijing_now)

    textbook = relationship("Textbook")
    student = relationship("User")


class TextbookConfig(Base):
    """教材订购配置（截止时间、关联通知等）"""
    __tablename__ = "textbook_config"

    id = Column(Integer, primary_key=True, index=True)
    deadline = Column(DateTime, nullable=True)
    notice_id = Column(Integer, nullable=True)
    contact_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=beijing_now)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class NoOrderConfirm(Base):
    """学生确认无需订购"""
    __tablename__ = "no_order_confirms"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, nullable=False, unique=True)
    created_at = Column(DateTime, default=beijing_now)


class QQConfig(Base):
    """QQ提醒配置（单条记录，key-value存储）"""
    __tablename__ = "qq_config"

    id = Column(Integer, primary_key=True, index=True)
    api_url = Column(String(300), nullable=False, default="")  # OneBot HTTP API 地址，如 http://127.0.0.1:5700
    group_id = Column(String(20), nullable=False, default="")   # 群聊 QQ 号
    enabled = Column(Integer, nullable=False, default=0)        # 0 关闭 1 开启
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)


class SiteStat(Base):
    """站点访问统计（单行记录）"""
    __tablename__ = "site_stats"

    id = Column(Integer, primary_key=True, index=True)
    total_visits = Column(Integer, nullable=False, default=0)
    total_pv = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=beijing_now, onupdate=beijing_now)
