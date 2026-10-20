"""Notification target, alert isolation and traffic defense regression cases."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import json
from fastapi import HTTPException

class NotificationCases:
    @contextmanager
    def delivery_fixture(self):
        from config import DATA_DIR
        from database import SessionLocal
        from models import User, QQConfig
        from security import WindowLimiter
        paths=[DATA_DIR/'qq-groups.json',DATA_DIR/'defense-settings.json']
        saved={p:p.read_bytes() if p.exists() else None for p in paths}
        with SessionLocal() as db:
            users=db.query(User).all();contacts={u.id:(u.email,u.qq_number,u.is_dorm_leader,u.dorm) for u in users}
            config=db.query(QQConfig).first()
            config_values=(config.id,config.api_url,config.group_id,config.enabled) if config else None
            if not config:config=QQConfig();db.add(config)
            config.api_url='http://napcat:3001?access_token=not-a-real-token';config.group_id='123456';config.enabled=1
            for user in users:user.email=f'user{user.id}@example.test';user.qq_number=str(100000+user.id)
            db.commit()
        try:
            with patch.object(WindowLimiter,'allow',return_value=True):yield
        finally:
            with SessionLocal() as db:
                for uid,values in contacts.items():
                    user=db.get(User,uid);user.email,user.qq_number,user.is_dorm_leader,user.dorm=values
                config=db.query(QQConfig).first()
                if config_values:config.api_url,config.group_id,config.enabled=config_values[1:]
                elif config:db.delete(config)
                db.commit()
            for path,value in saved.items():
                if value is None:path.unlink(missing_ok=True)
                else:path.write_bytes(value)

    def test_notify_multigroup_config_token_mask_and_target_permissions(self):
        from database import SessionLocal
        from models import QQConfig
        with self.delivery_fixture():
            payload={'api_url':'http://napcat:3001','access_token':'private-robot-token','enabled':1,'group_id':'123456',
                     'groups':[{'id':'123456','name':'班级群'},{'id':'654321','name':'班干群'}]}
            response=self.client.put('/api/qq-config',headers=self.leader,json=payload)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(len(response.json()['groups']),2);self.assertTrue(response.json()['token_configured'])
            self.assertNotIn('private-robot-token',response.text)
            self.assertNotIn('private-robot-token',self.client.get('/api/qq-config',headers=self.admin).text)
            payload['access_token']=''
            self.client.put('/api/qq-config',headers=self.leader,json=payload)
            with SessionLocal() as db:self.assertIn('private-robot-token',db.query(QQConfig).first().api_url)
            payload['groups'].append(payload['groups'][0])
            self.assertEqual(self.client.put('/api/qq-config',headers=self.leader,json=payload).status_code,422)
            self.assertEqual(self.client.get('/api/notifications/targets',params={'endpoint':'/api/qq/notice/1/notify'},headers=self.student).status_code,403)
            self.assertEqual(self.client.get('/api/notifications/targets',params={'endpoint':'https://evil.test'},headers=self.admin).status_code,422)
            with patch('services.qq._call_qq',return_value={'status':'ok','data':{'user_id':100000}}) as send:
                self.assertEqual(self.client.post('/api/qq-config/test',headers=self.leader).status_code,200)
                self.assertEqual(send.call_args.args[1],'get_login_info')

    def test_notify_selected_groups_only_and_partial_results(self):
        from services.private_settings import write_settings
        with self.delivery_fixture():
            write_settings('qq-groups.json',{'groups':[{'id':'123456','name':'A'},{'id':'654321','name':'B'}]})
            notice=self._ai_notice('<p>通知内容</p>')
            try:
                endpoint=f'/api/qq/notice/{notice}/notify'
                with patch('services.qq._send_qq_msg',return_value={'status':'ok'}) as send:
                    result=self.client.post(endpoint,headers=self.leader,json={'group_ids':['654321']})
                    self.assertEqual(result.status_code,200,result.text);self.assertEqual(send.call_count,1)
                    self.assertEqual(send.call_args.args[2]['group_id'],654321)
                    self.assertIs(send.call_args.args[2]['at_all'],False)
                    self.assertEqual(self.client.post(endpoint,headers=self.leader,json={'group_ids':['987654']}).status_code,422)
                    self.assertEqual(send.call_count,1)
                with patch('services.qq._send_qq_msg',side_effect=[{'status':'ok'},{'status':'failed','partial':True,'error':'附件发送失败'}]):
                    result=self.client.post(endpoint,headers=self.leader,json={'group_ids':['123456','654321']}).json()
                    self.assertEqual((result['sent'],result['failed']),(1,1));self.assertTrue(result['targets'][1]['partial'])
                self.assertEqual(self.client.post(endpoint,headers=self.leader,json={'group_ids':[]}).status_code,422)
            finally:self.client.delete(f'/api/notices/{notice}',headers=self.admin)

    def test_notify_mail_and_private_selection_rechecks_submission(self):
        with self.delivery_fixture():
            task=self.task()
            try:
                endpoint=f'/api/qq/file-task/{task}/remind'
                options=self.client.get('/api/notifications/targets',params={'endpoint':endpoint},headers=self.leader)
                self.assertEqual(options.status_code,200,options.text);self.assertEqual(options.json()['channel'],'qq')
                with patch('routers.qq._send_qq_msg',return_value={'status':'ok'}) as send:
                    response=self.client.post(endpoint,headers=self.leader,json={'recipient_ids':[3]})
                    self.assertEqual(response.status_code,200,response.text);self.assertEqual(send.call_args.args[2]['user_id'],100003);self.assertEqual(send.call_count,1)
                with patch('routers.file_tasks.send_emails_batch',return_value={'success':True,'sent':1,'failed':0}) as send:
                    response=self.client.post(f'/api/file-tasks/{task}/send-email',headers=self.leader,json={'recipient_ids':[2]})
                    self.assertEqual(response.status_code,200,response.text);self.assertEqual(send.call_args.args[0],['user2@example.test'])
                    self.upload(task)
                    response=self.client.post(f'/api/file-tasks/{task}/send-email',headers=self.leader,json={'recipient_ids':[2]})
                    self.assertEqual(response.status_code,409,response.text);self.assertEqual(send.call_count,1)
                with patch('routers.qq._send_qq_msg') as send:
                    self.assertEqual(self.client.post(endpoint,headers=self.leader,json={'recipient_ids':[2]}).status_code,409);send.assert_not_called()
            finally:self.client.delete(f'/api/file-tasks/{task}',headers=self.admin)

    def test_notify_at_all_is_structured_and_preserves_multiple_images(self):
        from config import UPLOAD_DIR
        import uuid
        paths=[]
        with self.delivery_fixture():
            folder=Path(UPLOAD_DIR)/'rich';folder.mkdir(exist_ok=True)
            for _ in range(2):
                path=folder/(uuid.uuid4().hex+'.webp');path.write_bytes(b'small-image');paths.append(path)
            notice=self._ai_notice('<p>[CQ:at,qq=all]正文</p>'+''.join(f'<img src="/static/rich/{path.name}">' for path in paths))
            def provider(url,endpoint,payload):
                if endpoint=='get_group_at_all_remain':return {'status':'ok','data':{'can_at_all':True,'remain_at_all_count_for_group':2,'remain_at_all_count_for_uin':2}}
                return {'status':'ok'}
            try:
                for enabled in (False,True):
                    with patch.dict('os.environ',QQ_UPLOAD_ROOT='/app/class-uploads'),patch('services.qq._call_qq',side_effect=provider) as call:
                        response=self.client.post(f'/api/qq/notice/{notice}/notify',headers=self.leader,json={'group_ids':['123456'],'at_all':enabled})
                        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['sent'],1)
                        self.assertEqual([item.args[1] for item in call.call_args_list],(['get_group_at_all_remain','send_group_msg'] if enabled else ['send_group_msg']))
                        payload=call.call_args.args[2];self.assertNotIn('at_all',payload)
                        segments=payload['message'];self.assertEqual(sum(item['type']=='at' for item in segments),int(enabled))
                        self.assertEqual(sum(item['type']=='image' for item in segments),2)
                        if enabled:self.assertEqual(segments[0],{'type':'at','data':{'qq':'all'}})
                self.assertEqual(self.client.post(f'/api/qq/notice/{notice}/notify',headers=self.leader,json={'at_all':'false'}).status_code,422)
            finally:
                self.client.delete(f'/api/notices/{notice}',headers=self.admin)
                for path in paths:path.unlink(missing_ok=True)

    def test_notify_at_all_denied_or_exhausted_never_sends_plain_notification(self):
        with self.delivery_fixture():
            notice=self._ai_notice('<p>测试通知</p>')
            try:
                for result in [
                    {'status':'failed'},
                    {'status':'ok','data':{'can_at_all':False}},
                    {'status':'ok','data':{'can_at_all':True,'remain_at_all_count_for_group':0}},
                    {'status':'ok','data':{'can_at_all':True,'remain_at_all_count_for_uin':0}},
                ]:
                    with patch('services.qq._call_qq',return_value=result) as call:
                        response=self.client.post(f'/api/qq/notice/{notice}/notify',headers=self.leader,json={'group_ids':['123456'],'at_all':True})
                        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['failed'],1)
                        self.assertIn('本群未发送',response.json()['message']);self.assertEqual(call.call_count,1)
                        self.assertEqual(call.call_args.args[1],'get_group_at_all_remain')
            finally:self.client.delete(f'/api/notices/{notice}',headers=self.admin)

    def test_notify_at_all_never_leaks_into_private_reminders(self):
        from services.qq import _send_qq_msg
        with patch('services.qq._call_qq',return_value={'status':'ok'}) as call:
            _send_qq_msg('http://napcat:3001','send_private_msg',{'user_id':123456,'message':'私信提醒','at_all':True})
            self.assertEqual(call.call_count,1);self.assertEqual(call.call_args.args[1],'send_private_msg')
            self.assertNotIn('at_all',call.call_args.args[2])
            self.assertFalse(any(item['type']=='at' for item in call.call_args.args[2]['message']))

    def test_notify_all_group_business_endpoints_respect_selection(self):
        from datetime import datetime
        from database import SessionLocal
        from models import Survey, GroupProject, Activity, ClassMeeting
        with self.delivery_fixture():
            with SessionLocal() as db:
                rows=[Survey(title='问卷',author_id=1),GroupProject(name='分组',admin_id=1),Activity(title='活动',start_time=datetime(2099,1,1),end_time=datetime(2099,1,2),author_id=1),ClassMeeting(title='班会',meeting_date=datetime(2099,1,1),author_id=1)]
                db.add_all(rows);db.commit();ids=[row.id for row in rows]
            try:
                for kind,uid in zip(('survey','group-project','activity','class-meeting'),ids):
                    with patch('services.qq._send_qq_msg',return_value={'status':'ok'}) as send:
                        response=self.client.post(f'/api/qq/{kind}/{uid}/notify',headers=self.leader,json={'group_ids':['123456'],'at_all':True})
                        self.assertEqual(response.status_code,200,response.text);self.assertEqual(send.call_count,1)
                        self.assertIs(send.call_args.args[2]['at_all'],True)
            finally:
                with SessionLocal() as db:
                    for model,uid in zip((Survey,GroupProject,Activity,ClassMeeting),ids):db.delete(db.get(model,uid))
                    db.commit()

    def test_notify_activity_single_entry_cannot_remind_completed_person(self):
        from database import SessionLocal
        from models import Activity, ActivityParticipant
        from datetime import datetime
        with self.delivery_fixture():
            with SessionLocal() as db:
                activity=Activity(title='签到提醒',start_time=datetime(2099,1,1),end_time=datetime(2099,1,2),author_id=1)
                db.add(activity);db.flush();uid=activity.id
                db.add_all([ActivityParticipant(activity_id=uid,student_id=2,sign_status='absent'),ActivityParticipant(activity_id=uid,student_id=3,sign_status='signed')]);db.commit()
            try:
                endpoint=f'/api/qq/activity/{uid}/remind-one'
                with patch('routers.qq._send_qq_msg',return_value={'status':'ok'}) as send:
                    response=self.client.post(endpoint,headers=self.leader,json={'student_id':2,'recipient_ids':[2]})
                    self.assertEqual(response.status_code,200,response.text);self.assertEqual(send.call_count,1)
                    self.assertEqual(self.client.post(endpoint,headers=self.leader,json={'student_id':2,'recipient_ids':[3]}).status_code,409)
                    self.assertEqual(send.call_count,1)
            finally:
                with SessionLocal() as db:db.delete(db.get(Activity,uid));db.commit()

    def test_server_status_permissions_and_settings_bounds(self):
        from services.server_monitor import monitor
        with self.delivery_fixture():
            settings=dict(monitor.settings)
            try:
                self.assertEqual(self.client.get('/api/server/status',headers=self.student).status_code,403)
                response=self.client.get('/api/server/status',headers=self.leader)
                self.assertEqual(response.status_code,200,response.text);self.assertFalse(response.json()['can_configure'])
                self.assertIn('host_memory_available',response.json()['resources'])
                self.assertEqual(self.client.put('/api/server/defense-settings',headers=self.leader,json=settings).status_code,403)
                self.assertEqual(self.client.put('/api/server/defense-settings',headers=self.admin,json={**settings,'ip_per_10_seconds':1}).status_code,422)
                self.assertEqual(self.client.put('/api/server/defense-settings',headers=self.admin,json=settings).status_code,200)
            finally:monitor.settings=settings

    def test_defense_burst_blocks_only_attacker_and_recovers(self):
        from services.server_monitor import TrafficMonitor
        now=[100.0];monitor=TrafficMonitor(lambda:now[0]);monitor.settings_at=100
        for _ in range(300):
            self.assertEqual(monitor.enter('198.51.100.1','/api/notices'),0);monitor.leave('198.51.100.1','/api/notices',200)
        self.assertGreater(monitor.enter('198.51.100.1','/api/notices'),0)
        monitor.enter('198.51.100.1','/api/notices');monitor.enter('198.51.100.1','/api/notices')
        self.assertEqual(len(monitor.snapshot()['blocked_sources']),1)
        self.assertEqual(monitor.enter('198.51.100.2','/api/notices'),0);monitor.leave('198.51.100.2','/api/notices',200)
        self.assertIsNotNone(monitor.pending);self.assertEqual(len(monitor.events),1)
        self.assertEqual(monitor.events[-1]['action'],'临时封禁来源')
        self.assertEqual(monitor.pending['event']['action'],'临时封禁来源')
        now[0]+=301;monitor.settings_at=now[0]
        self.assertEqual(monitor.enter('198.51.100.1','/api/notices'),0);monitor.leave('198.51.100.1','/api/notices',200)
        self.assertEqual(monitor.inflight,0)

    def test_defense_shared_campus_and_failed_login_detection(self):
        from services.server_monitor import TrafficMonitor
        now=[100.0];monitor=TrafficMonitor(lambda:now[0]);monitor.settings_at=100
        # Fifty classmates issuing five requests together stay below the shared-IP burst budget.
        for _ in range(250):
            self.assertEqual(monitor.enter('198.51.100.4','/api/dashboard'),0);monitor.leave('198.51.100.4','/api/dashboard',200)
        for _ in range(30):
            self.assertEqual(monitor.enter('198.51.100.5','/api/login'),0);monitor.leave('198.51.100.5','/api/login',401)
        self.assertGreater(monitor.enter('198.51.100.5','/api/login'),0)
        self.assertIn('登录失败',monitor.events[-1]['reason'])
        self.assertEqual(monitor.enter('198.51.100.6','/api/dashboard'),0)

    def test_defense_alerts_all_leaders_and_admins_not_students_without_db_connection(self):
        from services.security_alerts import deliver_security_alert
        from database import engine
        with self.delivery_fixture():
            pending={'event':{'time':'2026-10-20T12:00:00','reason':'请求超限','peer':'198.51.100.1','path':'/api/notices','action':'限速'},'incidents':3,'channels':{}}
            def mail(addresses,*args,**kwargs):
                self.assertEqual(engine.pool.checkedout(),0)
                self.assertEqual(set(addresses),{'user1@example.test','user4@example.test'})
                return {'success':True,'sent':2,'failed':0}
            def qq(url,endpoint,payload):
                self.assertEqual(engine.pool.checkedout(),0);self.assertIn(payload['user_id'],{100001,100004});return {'status':'ok'}
            with patch('services.mailer.send_emails_batch',side_effect=mail) as mail_call,patch('services.qq._send_qq_msg',side_effect=qq) as qq_call:
                result=deliver_security_alert(pending);self.assertEqual(result['email']['sent'],2);self.assertEqual(result['qq']['sent'],2)
                self.assertEqual(mail_call.call_count,1);self.assertEqual(qq_call.call_count,2)

    def test_defense_alert_busy_retry_dedup_and_cooldown(self):
        from services.server_monitor import TrafficMonitor
        now=[100.0];monitor=TrafficMonitor(lambda:now[0]);monitor.settings_at=100
        with monitor.lock:monitor.incident('198.51.100.1','请求超限','/api/notices','限速')
        with patch('services.security_alerts.deliver_security_alert',side_effect=[{'email':{'sent':0,'failed':2,'retry':True}},{'email':{'sent':2,'failed':0,'retry':False}}]) as send,patch('services.server_monitor.write_settings'):
            monitor.flush();self.assertIsNotNone(monitor.pending)
            monitor.flush();self.assertEqual(send.call_count,1)
            now[0]+=16;monitor.flush();self.assertIsNone(monitor.pending);self.assertEqual(len(monitor.alerts),1)
            with monitor.lock:monitor.incident('198.51.100.2','请求超限','/api/notices','限速')
            monitor.flush();self.assertEqual(send.call_count,2);self.assertIsNone(monitor.pending)
            now[0]+=301
            with monitor.lock:monitor.incident('198.51.100.2','请求超限','/api/notices','限速')
            self.assertIsNotNone(monitor.pending)

    def test_notify_notice_and_survey_selected_mail_and_private(self):
        with self.delivery_fixture():
            notice=self._ai_notice('<p>多图通知原文</p>')
            survey,_=self.survey()
            try:
                for kind,uid in [('notice',notice),('survey',survey['id'])]:
                    with patch('routers.qq._send_qq_msg',return_value={'status':'ok'}) as send:
                        response=self.client.post(f'/api/qq/{kind}/{uid}/remind',headers=self.leader,json={'recipient_ids':[3]})
                        self.assertEqual(response.status_code,200,response.text)
                        self.assertEqual(send.call_count,1);self.assertEqual(send.call_args.args[2]['user_id'],100003)
                for kind,uid,module in [('notices',notice,'settings'),('surveys',survey['id'],'surveys')]:
                    with patch(f'routers.{module}.send_emails_batch',return_value={'success':True,'sent':1,'failed':0}) as send:
                        response=self.client.post(f'/api/{kind}/{uid}/send-email',headers=self.leader,json={'recipient_ids':[3]})
                        self.assertEqual(response.status_code,200,response.text)
                        self.assertEqual(send.call_args.args[0],['user3@example.test'])
            finally:
                self.client.delete(f'/api/notices/{notice}',headers=self.admin)
                self.client.delete(f'/api/surveys/{survey["id"]}',headers=self.admin)

    def test_notify_textbook_personal_and_dorm_content_isolated(self):
        from database import SessionLocal
        from models import Textbook,TextbookOrder,User
        with self.delivery_fixture():
            with SessionLocal() as db:
                for uid in (2,3):
                    user=db.get(User,uid);user.dorm=f'TEST-{uid}';user.is_dorm_leader=True
                    book=Textbook(name=f'教材-{uid}',discounted_price=uid);db.add(book);db.flush()
                    db.add(TextbookOrder(student_id=uid,textbook_id=book.id))
                db.commit();books=[r.id for r in db.query(Textbook).filter(Textbook.name.like('教材-%'))]
            try:
                for suffix in ('send-emails','send-dorm-emails'):
                    with patch('routers.textbooks.send_emails_batch',return_value={'success':True,'sent':1,'failed':0}) as send:
                        response=self.client.post('/api/textbooks/orders/'+suffix,headers=self.leader,json={'recipient_ids':[3]})
                        self.assertEqual(response.status_code,200,response.text);self.assertEqual(send.call_count,1)
                        self.assertEqual(send.call_args.args[0],['user3@example.test'])
                        self.assertIn('教材-3',send.call_args.args[2]);self.assertNotIn('教材-2',send.call_args.args[2])
                with patch('routers.textbooks._send_qq_msg') as send:
                    response=self.client.post('/api/textbooks/qq-remind-unordered',headers=self.leader,json={'recipient_ids':[2]})
                    self.assertEqual(response.status_code,409,response.text);send.assert_not_called()
            finally:
                with SessionLocal() as db:
                    db.query(TextbookOrder).filter(TextbookOrder.textbook_id.in_(books)).delete(synchronize_session=False)
                    db.query(Textbook).filter(Textbook.id.in_(books)).delete(synchronize_session=False);db.commit()

    def test_notify_meeting_selected_recipients_keep_attachment(self):
        from database import SessionLocal
        from models import ClassMeeting,ClassMeetingRecord
        from config import UPLOAD_DIR
        from datetime import datetime
        path=Path(UPLOAD_DIR)/('meeting_doc_'+'9'*32+'.pdf');path.write_bytes(b'pdf-test')
        with self.delivery_fixture():
            with SessionLocal() as db:
                meeting=ClassMeeting(title='选定接收班会记录',meeting_date=datetime(2099,1,1),author_id=1)
                db.add(meeting);db.flush();uid=meeting.id
                db.add(ClassMeetingRecord(meeting_id=uid,record_file=path.name,record_file_name='记录.pdf'));db.commit()
            try:
                with patch('routers.meetings.send_emails_batch',return_value={'success':True,'sent':1,'failed':0}) as send:
                    response=self.client.post(f'/api/class-meetings/{uid}/send-email',headers=self.leader,json={'recipient_ids':[3],'email':'not-selected@example.test'})
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(send.call_args.args[0],['user3@example.test'])
                    self.assertEqual(send.call_args.kwargs['attachments'][0]['name'],'记录.pdf')
            finally:
                path.unlink(missing_ok=True)
                self.client.delete(f'/api/class-meetings/{uid}',headers=self.admin)

    def test_defense_global_surges_bounded_sources_and_ipv6_login(self):
        from services.server_monitor import TrafficMonitor
        monitor=TrafficMonitor(lambda:100.0);monitor.settings_at=100
        monitor.settings['global_per_10_seconds']=600
        for i in range(600):
            peer=f'2001:db8::{i+1:x}';self.assertEqual(monitor.enter(peer,'/api/notices'),0);monitor.leave(peer,'/api/notices',200)
        self.assertGreater(monitor.enter('198.51.100.99','/api/notices'),0)
        self.assertEqual(monitor.events[-1]['reason'],'全站请求突增')
        monitor.settings['enabled']=False
        for i in range(4200):
            peer=f'2001:db8:1::{i+1:x}';monitor.enter(peer,'/api/notices');monitor.leave(peer,'/api/notices',200)
        self.assertEqual(len(monitor.peers),4096);self.assertEqual(monitor.inflight,0)
        monitor=TrafficMonitor(lambda:100.0);monitor.settings_at=100
        for i in range(30):
            monitor.enter('2001:0db8:0:0::1','/api/login');monitor.leave('2001:0db8:0:0::1','/api/login',401)
        self.assertGreater(monitor.enter('2001:db8::1','/api/login'),0)

    def test_defense_middleware_returns_retry_header_without_calling_app(self):
        import asyncio
        from security import SecurityMiddleware
        from services.server_monitor import TrafficMonitor
        monitor=TrafficMonitor(lambda:100.0);monitor.settings_at=100
        called=[];responses=[]
        async def app(scope,receive,send):called.append(scope)
        async def send(message):responses.append(message)
        async def receive():return {'type':'http.request','body':b''}
        # An untrusted forwarded header never becomes a peer inside this middleware.
        scope={'type':'http','method':'GET','path':'/api/notices','client':('198.51.100.1',123),'scheme':'https',
               'headers':[(b'x-forwarded-for',b'198.51.100.222')]}
        for _ in range(300):monitor.enter('198.51.100.1','/api/notices');monitor.leave('198.51.100.1','/api/notices',200)
        with patch('services.server_monitor.monitor',monitor):asyncio.run(SecurityMiddleware(app)(scope,receive,send))
        self.assertEqual(called,[]);self.assertEqual(responses[0]['status'],429)
        self.assertIn(b'retry-after',dict(responses[0]['headers']))
        self.assertNotIn('198.51.100.222',monitor.peers)

    def test_defense_real_channel_retry_does_not_repeat_attempted_recipients(self):
        from services.security_alerts import deliver_security_alert
        pending={'event':{'time':'2026-10-20','reason':'超限','peer':'198.51.100.1','path':'/api/login','action':'封禁'},'incidents':1,'channels':{}}
        with self.delivery_fixture():
            with patch('services.mailer.send_emails_batch',return_value={'success':True,'sent':1,'failed':1}) as mail,patch('services.qq._send_qq_msg',side_effect=[{'status':'failed'},HTTPException(503,'busy'),{'status':'ok'}]) as qq:
                pending['channels'].update(deliver_security_alert(pending))
                self.assertEqual(pending['channels']['email']['state'],'部分失败')
                pending['channels'].update(deliver_security_alert(pending))
                self.assertEqual(mail.call_count,1);self.assertEqual(qq.call_count,3)
                self.assertEqual([call.args[2]['user_id'] for call in qq.call_args_list],[100001,100004,100004])
                self.assertEqual(pending['channels']['qq']['sent'],1)

    def test_defense_preparation_failure_retries_are_bounded(self):
        from services.server_monitor import TrafficMonitor
        now=[100.0];monitor=TrafficMonitor(lambda:now[0]);monitor.settings_at=100
        with monitor.lock:monitor.incident('198.51.100.1','超限','/api/notices','限速')
        with patch('services.security_alerts.deliver_security_alert',side_effect=RuntimeError('private-secret')),patch('services.server_monitor.write_settings'):
            for _ in range(3):monitor.flush();now[0]+=16
        self.assertIsNone(monitor.pending);self.assertEqual(len(monitor.alerts),1)
        self.assertNotIn('private-secret',json.dumps(monitor.snapshot()))
