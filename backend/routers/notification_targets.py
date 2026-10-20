"""Read-only delivery preview; use the same eligibility rules again when sending."""
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from auth import require_admin
from database import get_db
from models import (User, Notice, FileTask, FileSubmission, Survey, SurveyQuestion, SurveyResponse,
    GroupProject, GroupAssignment, Activity, ActivityParticipant, ClassMeeting, QQConfig,
    TextbookOrder, NoOrderConfirm, EmailHistory)
from services.delivery import qq_groups

router = APIRouter(tags=['notification-targets'])


def target_users(db, endpoint):
    channel = 'email'
    scope = '全班同学'
    candidates = db.query(User).filter(User.role == 'student')
    match = re.fullmatch(r'/api/qq/(notice|file-task|survey|group-project|activity|class-meeting)/(\d+)/(notify|remind|remind-one|remind-leaders)', endpoint)
    if match:
        kind, value, action = match.groups(); value = int(value)
        model = {'notice':Notice,'file-task':FileTask,'survey':Survey,'group-project':GroupProject,'activity':Activity,'class-meeting':ClassMeeting}[kind]
        entity = db.get(model, value)
        if not entity: raise HTTPException(404, '通知关联事项已删除')
        if action == 'notify': return 'group', [], '已配置的 QQ 群'
        channel = 'qq'
    else:
        match = re.fullmatch(r'/api/(notices|file-tasks|surveys|class-meetings)/(\d+)/send-email', endpoint)
        if match:
            kind, value = match.groups();value=int(value)
            kind = {'notices':'notice','file-tasks':'file-task','surveys':'survey','class-meetings':'class-meeting'}[kind]
            entity=db.get({'notice':Notice,'file-task':FileTask,'survey':Survey,'class-meeting':ClassMeeting}[kind],value)
            if not entity: raise HTTPException(404,'通知关联事项已删除')
            action='email'
        elif endpoint in {'/api/textbooks/qq-remind-unordered','/api/textbooks/qq-remind-unordered-email'}:
            ordered = {uid for uid, in db.query(TextbookOrder.student_id)} | {uid for uid, in db.query(NoOrderConfirm.student_id)}
            return ('qq' if endpoint.endswith('unordered') else 'email'), candidates.filter(User.id.notin_(ordered)).all(), '尚未订购且未确认无需订购的同学'
        elif endpoint == '/api/textbooks/orders/send-emails':
            return channel,candidates.filter(User.id.in_(db.query(TextbookOrder.student_id))).all(),'已有教材订购记录的同学'
        elif endpoint == '/api/textbooks/orders/send-dorm-emails':
            dorms = [dorm for dorm, in db.query(User.dorm).join(TextbookOrder,TextbookOrder.student_id==User.id).distinct()]
            users=[]
            for dorm in dorms:
                user=db.query(User).filter(User.dorm==dorm,User.is_dorm_leader==True).first()
                if user: users.append(user)
            return channel, users, '有订购记录宿舍的宿舍长（仅发送各自宿舍明细）'
        elif endpoint == '/api/email-history/resend':
            emails=[email for email, in db.query(EmailHistory.recipient_email).filter(EmailHistory.status=='failed').distinct()]
            return channel,db.query(User).filter(User.email.in_(emails)).all(),'有失败邮件记录的系统用户'
        else: raise HTTPException(422, '此接口不支持批量目标选择')
    if kind == 'file-task':
        candidates=candidates.filter(User.id.notin_(db.query(FileSubmission.student_id).filter(FileSubmission.task_id==value)))
        scope='尚未提交该文件任务的同学'
    elif kind == 'survey':
        answered=db.query(SurveyResponse.student_id).join(SurveyQuestion).filter(SurveyQuestion.survey_id==value)
        candidates=candidates.filter(User.id.notin_(answered));scope='尚未填写该问卷的同学'
    elif kind == 'group-project':
        candidates=candidates.filter(User.id.notin_(db.query(GroupAssignment.student_id).filter(GroupAssignment.project_id==value)))
        scope='尚未加入该项目分组的同学'
    elif kind == 'activity':
        candidates=candidates.filter(User.id.in_(db.query(ActivityParticipant.student_id).filter(ActivityParticipant.activity_id==value,ActivityParticipant.sign_status=='absent')))
        scope='此活动尚未签到的参与同学'
    elif kind == 'class-meeting' and action == 'remind-leaders':
        candidates=db.query(User).filter(User.id.in_([entity.attendance_leader_id,entity.host_leader_id]));scope='该班会安排的考勤与主持班干'
    elif kind == 'class-meeting':
        candidates=db.query(User);scope='选择接收班会记录的系统用户，也可保留原指定邮箱'
    return channel,candidates.order_by(User.student_id,User.id).all(),scope


@router.get('/api/notifications/targets')
def delivery_targets(endpoint: str = Query(max_length=200), db=Depends(get_db, scope='function'), current_user=Depends(require_admin)):
    channel,users,scope=target_users(db,endpoint)
    cfg=db.query(QQConfig).first()
    rows=[]
    for user in users:
        address=(user.qq_number if channel=='qq' else user.email) or ''
        available=bool(re.fullmatch(r'[1-9][0-9]{4,11}',address.strip())) if channel=='qq' else bool(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',address.strip()))
        rows.append({'id':user.id,'name':user.real_name or user.username,'student_id':user.student_id,
                     'address':address,'available':available})
    return {'channel':channel,'scope':scope,'users':rows,'groups':qq_groups(cfg) if channel=='group' else [],
            'default_group_id':cfg.group_id if cfg else '', 'qq_enabled':bool(cfg and cfg.enabled and cfg.api_url)}
