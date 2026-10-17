from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserBase(BaseModel):
    username: str
    real_name: str = ""
    student_id: str = ""
    political_status: str = ""
    email: str = ""
    qq_number: str = ""
    phone: str = ""
    dorm: str = ""
    class_position: str = ""
    show_in_committee: bool = False
    role: str = "student"
    is_class_leader: bool = False


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    student_id: Optional[str] = None
    political_status: Optional[str] = None
    email: Optional[str] = None
    qq_number: Optional[str] = None
    phone: Optional[str] = None
    dorm: Optional[str] = None
    class_position: Optional[str] = None
    show_in_committee: Optional[bool] = None
    is_class_leader: Optional[bool] = None
    is_dorm_leader: Optional[bool] = None


class UserSelfUpdate(BaseModel):
    real_name: Optional[str] = None
    political_status: Optional[str] = None
    email: Optional[str] = None
    qq_number: Optional[str] = None
    phone: Optional[str] = None
    dorm: Optional[str] = None
    class_position: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    real_name: str
    student_id: str
    political_status: str
    email: str
    qq_number: str
    phone: str = ""
    dorm: str = ""
    class_position: str = ""
    show_in_committee: bool = False
    is_class_leader: bool = False
    is_dorm_leader: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ClassCommitteeResponse(BaseModel):
    id: int
    real_name: str
    class_position: str = ""
    phone: str = ""
    qq_number: str = ""
    dorm: str = ""
    show_in_committee: bool = False
    sort_order: int = 0

    class Config:
        from_attributes = True


class ClassCommitteeUpdate(BaseModel):
    class_position: Optional[str] = None
    phone: Optional[str] = None
    qq_number: Optional[str] = None
    dorm: Optional[str] = None
    show_in_committee: Optional[bool] = None
    sort_order: Optional[int] = None


class CounselorInfoResponse(BaseModel):
    id: int
    name: str = ""
    office: str = ""
    phone: str = ""
    qq_number: str = ""

    class Config:
        from_attributes = True


class CounselorInfoUpdate(BaseModel):
    name: Optional[str] = None
    office: Optional[str] = None
    phone: Optional[str] = None
    qq_number: Optional[str] = None


class QQConfigCreate(BaseModel):
    api_url: str = ""
    group_id: str = ""
    enabled: int = 0


class QQConfigResponse(BaseModel):
    id: int
    api_url: str
    group_id: str
    enabled: int
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── 教材订购 ───

class TextbookBatchOrderRequest(BaseModel):
    textbook_ids: list[int]


class TextbookCreate(BaseModel):
    course_name: str = ""
    name: str
    isbn: str = ""
    publisher: str = ""
    author: str = ""
    course_type: str = "必修"
    original_price: float = 0.0
    discounted_price: float = 0.0
    notes: str = ""


class TextbookResponse(BaseModel):
    id: int
    course_name: str = ""
    name: str
    isbn: str = ""
    publisher: str = ""
    author: str = ""
    course_type: str
    original_price: float
    discounted_price: float
    notes: str
    created_at: datetime

    class Config:
        from_attributes = True


class TextbookOrderResponse(BaseModel):
    id: int
    textbook_id: int
    course_name: str = ""
    textbook_name: str = ""
    isbn: str = ""
    publisher: str = ""
    author: str = ""
    course_type: str = ""
    original_price: float = 0.0
    discounted_price: float = 0.0
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class TextbookConfigCreate(BaseModel):
    deadline: Optional[datetime] = None
    notice_id: Optional[int] = None
    contact_user_id: Optional[int] = None


class TextbookConfigResponse(BaseModel):
    id: int
    deadline: Optional[datetime] = None
    notice_id: Optional[int] = None
    contact_user_id: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True


class UserImportItem(BaseModel):
    username: str
    real_name: str
    student_id: str
    political_status: str = ""
    password: str


class NoticeCreate(BaseModel):
    title: str
    content: str
    is_urgent: bool = False


class NoticeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_urgent: Optional[bool] = None


class NoticeResponse(BaseModel):
    id: int
    title: str
    content: str
    is_urgent: bool = False
    created_at: datetime
    updated_at: datetime
    author_id: int
    author_name: str = ""
    author_qq: str = ""

    class Config:
        from_attributes = True


class GradeCreate(BaseModel):
    student_id: int
    score: float
    gpa: float
    semester: str
    academic_year: str
    class_rank: int = 0
    total_students: int = 0


class GradeUpdate(BaseModel):
    student_id: Optional[int] = None
    score: Optional[float] = None
    gpa: Optional[float] = None
    semester: Optional[str] = None
    academic_year: Optional[str] = None
    class_rank: Optional[int] = None
    total_students: Optional[int] = None


class GradeResponse(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    score: float
    gpa: float
    semester: str
    academic_year: str
    class_rank: int = 0
    total_students: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class GradeChangeRequestCreate(BaseModel):
    grade_id: Optional[int] = None
    proposed_score: float = 0.0
    proposed_gpa: float = 0.0
    proposed_semester: str = ""
    proposed_academic_year: str = ""
    proposed_class_rank: int = 0
    proposed_total_students: int = 0


class GradeChangeRequestResponse(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    grade_id: Optional[int] = None
    proposed_score: float
    proposed_gpa: float
    proposed_semester: str
    proposed_academic_year: str
    proposed_class_rank: int
    proposed_total_students: int
    status: str
    admin_id: Optional[int] = None
    admin_name: str = ""
    admin_comment: str = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GradeChangeRequestProcess(BaseModel):
    comment: str = ""


class CertificateResponse(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    award_name: str
    award_level: str
    award_date: Optional[datetime] = None
    image_path: str
    created_at: datetime

    class Config:
        from_attributes = True


class CertificateStats(BaseModel):
    total: int
    national_count: int
    provincial_count: int
    school_count: int
    student_count: int


class SocialPracticeCreate(BaseModel):
    student_id: int
    activity_name: str
    role: str = ""
    description: str = ""
    start_date: str
    end_date: str


class SocialPracticeUpdate(BaseModel):
    activity_name: Optional[str] = None
    role: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SocialPracticeResponse(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    activity_name: str
    role: str
    description: str
    start_date: datetime
    end_date: datetime
    certificate_image: str
    created_at: datetime

    class Config:
        from_attributes = True


class FileTaskCreate(BaseModel):
    title: str
    description: str = ""
    deadline: str
    naming_pattern: str = "{name}_{sid}"
    group_project_id: Optional[int] = None


class FileTaskResponse(BaseModel):
    id: int
    title: str
    description: str
    created_at: datetime
    deadline: datetime
    author_id: int
    author_name: str = ""
    author_qq: str = ""
    submission_count: int = 0
    naming_pattern: str = "{name}_{sid}"
    group_project_id: Optional[int] = None
    group_project_name: Optional[str] = None

    class Config:
        from_attributes = True


class FileSubmissionResponse(BaseModel):
    id: int
    task_id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    file_path: str
    original_name: str
    submitted_at: datetime

    class Config:
        from_attributes = True


class SurveyQuestionCreate(BaseModel):
    question_text: str
    description: str = ""
    question_type: str = "text"
    options: str = ""


class SurveyCreate(BaseModel):
    title: str
    description: str = ""
    deadline: Optional[str] = None
    is_anonymous: bool = False
    show_results: bool = True
    allow_multiple: bool = False
    questions: list[SurveyQuestionCreate] = []


class SurveyQuestionResponse(BaseModel):
    id: int
    survey_id: int
    question_text: str
    description: str = ""
    question_type: str
    options: str

    class Config:
        from_attributes = True


class SurveyResponse(BaseModel):
    id: int
    title: str
    description: str
    deadline: Optional[datetime] = None
    is_anonymous: bool = False
    show_results: bool = True
    allow_multiple: bool = False
    created_at: datetime
    author_id: int
    author_name: str = ""
    author_qq: str = ""
    response_count: int = 0
    questions: list[SurveyQuestionResponse] = []

    class Config:
        from_attributes = True


class SurveyAnswerItem(BaseModel):
    question_id: int
    answer_text: str


class SurveySubmitRequest(BaseModel):
    answers: list[SurveyAnswerItem]


class SurveyResultResponse(BaseModel):
    id: int
    question_text: str
    description: str = ""
    question_type: str
    options: str
    answers: list[str]
    vote_counts: dict = {}  # {option: count} 选项票数统计
    details: list[dict] = []  # [{student_name, student_id, answer, submitted_at}]


class SurveyResultListResponse(BaseModel):
    survey_id: int
    is_anonymous: bool = False
    show_results: bool = True
    allow_multiple: bool = False
    questions: list[SurveyResultResponse] = []


class ClassMeetingCreate(BaseModel):
    title: str
    meeting_date: str
    location: str = ""
    description: str = ""
    status: str = "upcoming"
    attendance_leader_id: Optional[int] = None
    host_leader_id: Optional[int] = None


class ClassMeetingUpdate(BaseModel):
    title: Optional[str] = None
    meeting_date: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    attendance_leader_id: Optional[int] = None
    host_leader_id: Optional[int] = None


class ClassMeetingResponse(BaseModel):
    id: int
    title: str
    meeting_date: datetime
    location: str
    description: str
    status: str
    created_at: datetime
    author_id: int
    author_name: str = ""
    record_text: str = ""
    record_images: list = []
    record_file: str = ""
    record_file_name: str = ""
    attendance_leader_id: Optional[int] = None
    attendance_leader_name: str = ""
    host_leader_id: Optional[int] = None
    host_leader_name: str = ""

    class Config:
        from_attributes = True


class MeetingRecordUpdate(BaseModel):
    record_text: str = ""
    images: list[str] = []


class BatchDeleteRequest(BaseModel):
    from_date: str
    to_date: str


class ResourceCategoryCreate(BaseModel):
    name: str
    description: str = ""


class ResourceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ResourceCategoryResponse(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime
    file_count: int = 0

    class Config:
        from_attributes = True


class ResourceFileResponse(BaseModel):
    id: int
    category_id: int
    category_name: str = ""
    filename: str
    original_name: str
    file_path: str
    file_size: int
    file_type: str
    visibility: str = "student"
    uploaded_by: int
    uploader_name: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# ─── 分组管理 ───
class GroupProjectCreate(BaseModel):
    name: str
    group_count: int = 4
    members_per_group: int = 6
    group_capacities: list[int] | None = None  # 每组容量，如 [6, 5, 7, 6]
    group_names: dict[str, str] | None = None  # 自定义组名，如 {"1": "学霸组", "2": "勤奋组"}
    deadline: Optional[str] = None


class GroupProjectResponse(BaseModel):
    id: int
    name: str
    group_count: int
    members_per_group: int
    group_capacities: list[int] | None = None
    group_names: dict[str, str] | None = None
    deadline: Optional[datetime] = None
    created_at: datetime
    admin_id: int
    total_assigned: int = 0

    class Config:
        from_attributes = True


class GroupAssignmentResponse(BaseModel):
    id: int
    project_id: int
    group_number: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    role: str = "member"

    class Config:
        from_attributes = True


class GroupProjectDetailResponse(BaseModel):
    id: int
    name: str
    group_count: int
    members_per_group: int
    group_capacities: list[int] | None = None
    group_names: dict[str, str] | None = None
    deadline: Optional[datetime] = None
    created_at: datetime
    groups: list[list[GroupAssignmentResponse]] = []

    class Config:
        from_attributes = True


class GroupJoinRequest(BaseModel):
    group_number: int
    role: str = "member"  # "leader" 或 "member"


class GroupProjectUpdate(BaseModel):
    group_names: dict[str, str] | None = None  # 自定义组名，如 {"1": "学霸组", "2": "勤奋组"}


# ─── SMTP 邮件配置 ───
class CheckinVerifyRequest(BaseModel):
    code: str
    activity_id: int


class ParticipantResponse(BaseModel):
    id: int
    student_id: int
    student_name: str = ""
    student_student_id: str = ""
    political_status: str = ""
    student_qq: str = ""
    sign_status: str
    sign_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActivityCreate(BaseModel):
    title: str
    description: str = ""
    location: str = ""
    start_time: str
    end_time: str
    checkin_mode: str = "auto"
    checkin_interval: int = 2


class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    checkin_mode: Optional[str] = None
    checkin_interval: Optional[int] = None


class ActivityResponse(BaseModel):
    id: int
    title: str
    description: str
    location: str
    start_time: datetime
    end_time: datetime
    qr_token: str = ""
    checkin_code: str = ""
    checkin_mode: str = "auto"
    checkin_interval: int = 2
    author_id: int
    author_name: str = ""
    participant_count: int = 0
    signed_count: int = 0
    my_sign_status: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class SmtpConfigCreate(BaseModel):
    host: str = "smtp.qq.com"
    port: int = 587
    username: str = ""
    password: str = ""


class SmtpConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    configured: bool  # 是否已配置（密码已设置）


class EmailHistoryResponse(BaseModel):
    id: int
    recipient_email: str
    recipient_name: str
    subject: str
    send_type: str
    related_id: Optional[int] = None
    status: str
    error_message: str
    created_at: datetime

    class Config:
        from_attributes = True
