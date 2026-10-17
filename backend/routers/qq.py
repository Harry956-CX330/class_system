from auth import require_admin
from config import ZIP_BATCH_MAX_SIZE, MAX_IMPORT_BYTES
from database import get_db
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response, StreamingResponse
from models import Activity
from models import ActivityParticipant
from models import ClassMeeting
from models import FileSubmission
from models import FileTask
from models import GroupAssignment
from models import GroupProject
from models import Notice
from models import QQConfig
from models import Survey
from models import SurveyQuestion
from models import SurveyResponse
from models import User
from schemas import QQConfigCreate
from schemas import QQConfigResponse
from services.files import build_zip_response, safe_upload_path, save_upload
from services.mailer import load_smtp_config, save_smtp_config, send_emails_batch
from services.qq import _get_qq_config
from services.qq import _get_qq_config, _send_qq_msg
from services.qq import _send_qq_msg
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

router = APIRouter(tags=["qq"])


@router.get("/api/qq-config", response_model=QQConfigResponse)
def get_qq_config(db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    cfg = db.query(QQConfig).first()
    if not cfg:
        cfg = QQConfig(api_url="", group_id="", enabled=0)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg



@router.put("/api/qq-config", response_model=QQConfigResponse)
def update_qq_config(data: QQConfigCreate, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    cfg = db.query(QQConfig).first()
    if not cfg:
        cfg = QQConfig()
        db.add(cfg)
    cfg.api_url = data.api_url
    cfg.group_id = data.group_id
    cfg.enabled = data.enabled
    db.commit()
    db.refresh(cfg)
    return cfg



@router.post("/api/qq/file-task/{task_id}/notify")
def qq_notify_file_task(task_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：新布置的文件任务"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    deadline_str = task.deadline.strftime("%Y-%m-%d %H:%M") if task.deadline else "无截止"
    msg = (
        f"【数科2441班·文件任务通知】\n"
        f"任务：{task.title}\n"
        f"截止时间：{deadline_str}\n"
        f"说明：{task.description or '无'}\n"
        f"发布人：{current_user.real_name}（QQ: {current_user.qq_number or '未填写'}）\n\n"
        f"请同学们按时提交文件！"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "群通知已发送", "result": result}



@router.post("/api/qq/file-task/{task_id}/remind")
def qq_remind_file_task(task_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：未提交文件任务的学生"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    task = db.query(FileTask).filter(FileTask.id == task_id).first()
    if not task: raise HTTPException(status_code=404, detail="任务不存在")
    # 已提交的学生
    submitted_ids = set(
        s[0] for s in db.query(FileSubmission.student_id).filter(FileSubmission.task_id == task_id).distinct().all()
    )
    unsubmitted = db.query(User).filter(User.role == "student", User.id.notin_(submitted_ids), User.qq_number != "").all() if submitted_ids \
        else db.query(User).filter(User.role == "student", User.qq_number != "").all()
    if not unsubmitted:
        return {"message": "所有学生均已提交或无QQ号", "sent": 0, "failed": 0}
    deadline_str = task.deadline.strftime("%m月%d日 %H:%M") if task.deadline else ""
    sent, failed = 0, 0
    for student in unsubmitted:
        if not student.qq_number.strip():
            continue
        msg = (
            f"【数科2441班·作业提醒】\n"
            f"同学 {student.real_name}，你好！\n"
            f"文件任务「{task.title}」{'截止 ' + deadline_str if deadline_str else ''}你尚未提交，请尽快完成。\n{task.description or ''}"
        )
        result = _send_qq_msg(cfg.api_url, "send_private_msg", {
            "user_id": int(student.qq_number.strip()),
            "message": msg,
        })
        if result.get("status") == "ok" or result.get("retcode") == 0:
            sent += 1
        else:
            failed += 1
    return {"message": f"私聊提醒完成：成功 {sent} 人，失败 {failed} 人", "sent": sent, "failed": failed}



@router.post("/api/qq/survey/{survey_id}/notify")
def qq_notify_survey(survey_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：新发布的调查问卷"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey: raise HTTPException(status_code=404, detail="问卷不存在")
    deadline_str = survey.deadline.strftime("%Y-%m-%d %H:%M") if survey.deadline else "无截止"
    msg = (
        f"【数科2441班·问卷通知】\n"
        f"问卷：{survey.title}\n"
        f"截止时间：{deadline_str}\n"
        f"说明：{survey.description or '无'}\n"
        f"发布人：{current_user.real_name}（QQ: {current_user.qq_number or '未填写'}）\n\n"
        f"请同学们及时填写问卷！"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "群通知已发送", "result": result}



@router.post("/api/qq/survey/{survey_id}/remind")
def qq_remind_survey(survey_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：未填写问卷的学生"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    survey = db.query(Survey).filter(Survey.id == survey_id).first()
    if not survey: raise HTTPException(status_code=404, detail="问卷不存在")
    # 已填写的学生（任一题目作答即算已填）
    answered_ids = set(
        r[0] for r in db.query(SurveyResponse.student_id).join(SurveyQuestion).filter(SurveyQuestion.survey_id == survey_id).distinct().all()
    )
    unsubmitted = db.query(User).filter(User.role == "student", User.id.notin_(answered_ids), User.qq_number != "").all() if answered_ids \
        else db.query(User).filter(User.role == "student", User.qq_number != "").all()
    if not unsubmitted:
        return {"message": "所有学生均已填写或无QQ号", "sent": 0, "failed": 0}
    deadline_str = survey.deadline.strftime("%m月%d日 %H:%M") if survey.deadline else ""
    sent, failed = 0, 0
    for student in unsubmitted:
        if not student.qq_number.strip():
            continue
        msg = (
            f"【数科2441班·问卷提醒】\n"
            f"同学 {student.real_name}，你好！\n"
            f"问卷「{survey.title}」{'截止 ' + deadline_str if deadline_str else ''}你尚未填写，请尽快完成。\n{survey.description or ''}"
        )
        result = _send_qq_msg(cfg.api_url, "send_private_msg", {
            "user_id": int(student.qq_number.strip()),
            "message": msg,
        })
        if result.get("status") == "ok" or result.get("retcode") == 0:
            sent += 1
        else:
            failed += 1
    return {"message": f"私聊提醒完成：成功 {sent} 人，失败 {failed} 人", "sent": sent, "failed": failed}



@router.post("/api/qq/notice/{notice_id}/notify")
def qq_notify_notice(notice_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：新发布的公告"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice: raise HTTPException(status_code=404, detail="公告不存在")
    msg = (
        f"【数科2441班·公告通知】\n"
        f"标题：{notice.title}\n"
        f"发布人：{current_user.real_name}（QQ: {current_user.qq_number or '未填写'}）\n\n"
        f"{notice.content}\n\n"
        f"请同学们及时查阅！"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "QQ群通知已发送", "result": result}



@router.post("/api/qq/group-project/{project_id}/notify")
def qq_notify_group_project(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：新发布的分组项目"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="分组项目不存在")
    deadline_str = project.deadline.strftime("%Y-%m-%d %H:%M") if project.deadline else "无截止"
    msg = (
        f"【数科2441班·分组通知】\n"
        f"项目：{project.name}\n"
        f"分组：共 {project.group_count} 组，每组 {project.members_per_group} 人\n"
        f"截止时间：{deadline_str}\n\n"
        f"请同学们尽快选择加入小组！截止后系统将自动分配。"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "QQ群通知已发送", "result": result}



@router.post("/api/qq/group-project/{project_id}/remind")
def qq_remind_group_project(project_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：未加入分组的学生"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    project = db.query(GroupProject).filter(GroupProject.id == project_id).first()
    if not project: raise HTTPException(status_code=404, detail="分组项目不存在")
    assigned_ids = set(
        a[0] for a in db.query(GroupAssignment.student_id).filter(GroupAssignment.project_id == project_id).all()
    )
    unassigned = db.query(User).filter(User.role == "student", User.id.notin_(assigned_ids), User.qq_number != "").all() if assigned_ids \
        else db.query(User).filter(User.role == "student", User.qq_number != "").all()
    if not unassigned:
        return {"message": "所有学生均已入组或无QQ号", "sent": 0, "failed": 0}
    deadline_str = project.deadline.strftime("%m月%d日 %H:%M") if project.deadline else ""
    sent, failed = 0, 0
    for student in unassigned:
        if not student.qq_number.strip():
            continue
        msg = (
            f"【数科2441班·分组提醒】\n"
            f"同学 {student.real_name}，你好！\n"
            f"分组项目「{project.name}」{'截止 ' + deadline_str if deadline_str else ''}你尚未加入小组，请尽快选择。"
        )
        result = _send_qq_msg(cfg.api_url, "send_private_msg", {
            "user_id": int(student.qq_number.strip()),
            "message": msg,
        })
        if result.get("status") == "ok" or result.get("retcode") == 0:
            sent += 1
        else:
            failed += 1
    return {"message": f"私聊提醒完成：成功 {sent} 人，失败 {failed} 人", "sent": sent, "failed": failed}



@router.post("/api/qq/activity/{activity_id}/notify")
def qq_notify_activity(activity_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：活动签到开始提醒"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    time_str = act.start_time.strftime("%Y-%m-%d %H:%M") if act.start_time else ""
    msg = (
        f"【数科2441班·活动签到通知】\n"
        f"活动：{act.title}\n"
        f"时间：{time_str or '待定'}\n"
        f"地点：{act.location or '待定'}\n"
        f"发布人：{current_user.real_name}（QQ: {current_user.qq_number or '未填写'}）\n\n"
        f"请同学们登录系统，输入老师展示的四位数字签到码完成签到！"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "QQ群通知已发送", "result": result}



@router.post("/api/qq/activity/{activity_id}/remind")
def qq_remind_activity(activity_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：一键提醒所有未签到学生"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    unsigned = db.query(User).join(ActivityParticipant, ActivityParticipant.student_id == User.id).filter(
        ActivityParticipant.activity_id == activity_id,
        ActivityParticipant.sign_status == "absent",
        User.qq_number != "",
    ).all()
    if not unsigned:
        return {"message": "所有学生均已签到或无QQ号", "sent": 0, "failed": 0}
    time_str = act.start_time.strftime("%m月%d日 %H:%M") if act.start_time else ""
    sent, failed = 0, 0
    for student in unsigned:
        if not student.qq_number.strip():
            continue
        msg = (
            f"【数科2441班·签到提醒】\n"
            f"同学 {student.real_name}，你好！\n"
            f"活动「{act.title}」{'（' + time_str + '）' if time_str else ''}你尚未签到，请尽快登录系统完成签到。"
        )
        result = _send_qq_msg(cfg.api_url, "send_private_msg", {
            "user_id": int(student.qq_number.strip()),
            "message": msg,
        })
        if result.get("status") == "ok" or result.get("retcode") == 0:
            sent += 1
        else:
            failed += 1
    return {"message": f"私聊提醒完成：成功 {sent} 人，失败 {failed} 人", "sent": sent, "failed": failed}



@router.post("/api/qq/activity/{activity_id}/remind-one")
def qq_remind_activity_one(activity_id: int, data: dict, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：单个未签到学生"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    act = db.query(Activity).filter(Activity.id == activity_id).first()
    if not act: raise HTTPException(status_code=404, detail="活动不存在")
    student = db.query(User).filter(User.id == data.get("student_id"), User.role == "student").first()
    if not student: raise HTTPException(status_code=404, detail="学生不存在")
    if not student.qq_number or not student.qq_number.strip():
        raise HTTPException(status_code=400, detail="该学生未填写QQ号")
    time_str = act.start_time.strftime("%m月%d日 %H:%M") if act.start_time else ""
    msg = (
        f"【数科2441班·签到提醒】\n"
        f"同学 {student.real_name}，你好！\n"
        f"活动「{act.title}」{'（' + time_str + '）' if time_str else ''}你尚未签到，请尽快登录系统完成签到。"
    )
    result = _send_qq_msg(cfg.api_url, "send_private_msg", {
        "user_id": int(student.qq_number.strip()),
        "message": msg,
    })
    if result.get("status") == "ok" or result.get("retcode") == 0:
        return {"message": "私聊提醒已发送", "result": result}
    return {"message": "发送失败", "result": result}



@router.post("/api/qq/class-meeting/{meeting_id}/notify")
def qq_notify_class_meeting(meeting_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """群聊通知：班会提醒"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting: raise HTTPException(status_code=404, detail="班会不存在")
    time_str = meeting.meeting_date.strftime("%Y-%m-%d %H:%M") if meeting.meeting_date else ""
    msg = (
        f"【数科2441班·班会通知】\n"
        f"班会：{meeting.title}\n"
        f"时间：{time_str or '待定'}\n"
        f"地点：{meeting.location or '待定'}\n"
        f"发布人：{current_user.real_name}（QQ: {current_user.qq_number or '未填写'}）\n\n"
        f"请同学们按时参加班会！"
    )
    result = _send_qq_msg(cfg.api_url, "send_group_msg", {
        "group_id": int(cfg.group_id),
        "message": msg,
    })
    _check_result(result)
    return {"message": "QQ群通知已发送", "result": result}



@router.post("/api/qq/class-meeting/{meeting_id}/remind-leaders")
def qq_remind_class_meeting_leaders(meeting_id: int, db: Session = Depends(get_db, scope="function"), current_user: User = Depends(require_admin)):
    """私聊提醒：考勤班干 + 主持/记录班干"""
    cfg = _get_qq_config(db)
    if not cfg: raise HTTPException(status_code=400, detail="QQ提醒未启用或未配置")
    meeting = db.query(ClassMeeting).filter(ClassMeeting.id == meeting_id).first()
    if not meeting: raise HTTPException(status_code=404, detail="班会不存在")
    leader_ids = list(dict.fromkeys([
        meeting.attendance_leader_id, meeting.host_leader_id,
    ]))
    leader_ids = [uid for uid in leader_ids if uid]
    if not leader_ids:
        raise HTTPException(status_code=400, detail="请先在班会中设置考勤班干和主持班干")
    time_str = meeting.meeting_date.strftime("%m月%d日 %H:%M") if meeting.meeting_date else ""
    sent, failed = 0, 0
    failures = []
    for uid in leader_ids:
        leader = db.query(User).filter(User.id == uid).first()
        if not leader or not leader.qq_number or not leader.qq_number.strip():
            failed += 1
            failures.append(f"{leader.real_name if leader else uid}（未填写QQ号）")
            continue
        roles = []
        if meeting.attendance_leader_id == uid:
            roles.append("考勤")
        if meeting.host_leader_id == uid:
            roles.append("主持/记录")
        role_txt = "、".join(roles)
        msg = (
            f"【数科2441班·班委任务提醒】\n"
            f"{leader.real_name}，你好！\n"
            f"你被安排负责班会「{meeting.title}」{'（' + time_str + '）' if time_str else ''}的{role_txt}工作，请提前准备。"
        )
        result = _send_qq_msg(cfg.api_url, "send_private_msg", {
            "user_id": int(leader.qq_number.strip()),
            "message": msg,
        })
        if result.get("status") == "ok" or result.get("retcode") == 0:
            sent += 1
        else:
            failed += 1
            failures.append(f"{leader.real_name}（发送失败）")
    detail = "；".join(failures) if failures else ""
    return {
        "message": f"班委私信提醒完成：成功 {sent} 人，失败 {failed} 人" + (f"（{detail}）" if detail else ""),
        "sent": sent, "failed": failed,
    }



def _check_result(result):
    if not (result.get("status")=="ok" or result.get("retcode")==0):
        raise HTTPException(502,result.get("error") or "QQ 服务未确认发送成功，请检查机器人状态")
