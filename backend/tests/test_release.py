"""Run against a disposable DB only: python -m unittest discover -s backend/tests -v."""
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

workspace = tempfile.TemporaryDirectory(prefix="class-system-tests-")
root = Path(workspace.name)
os.environ.update(DATABASE_URL="sqlite:///"+(root/"test.db").as_posix(),DATA_DIR=str(root/"data"),UPLOAD_DIR=str(root/"uploads"),TEMP_DIR=str(root/"tmp"),SECRET_KEY="test-only-secret-key-"+"x"*40,PUBLIC_BASE_URL="https://class.example.test",DOWNLOAD_KIB_PER_SECOND="100000")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from database import Base, engine, SessionLocal
from models import User, FileSubmission, SurveyQuestion, SurveyResponse
from auth import create_access_token, get_password_hash
from main import app
from fastapi.testclient import TestClient
from services.richtext import clean_html
from services.naming import safe_component, validate_pattern
from services.notifications import build_email
from routers.transfers import make_ticket
from fastapi import HTTPException

class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(engine)  # Disposable test DB, never the supplied data.db.
        with SessionLocal() as db:
            hashed = get_password_hash("TestPassword123!")
            db.add_all([User(id=1,username="admin-test",hashed_password=hashed,role="admin",student_id="A"),User(id=2,username="student-test",real_name="张三",hashed_password=hashed,role="student",student_id="20260002"),User(id=3,username="other-test",hashed_password=hashed,role="student",student_id="20260003")])
            db.commit()
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.admin = {"Authorization":"Bearer "+create_access_token({"user_id":1})}
        cls.student = {"Authorization":"Bearer "+create_access_token({"user_id":2})}
        cls.other = {"Authorization":"Bearer "+create_access_token({"user_id":3})}
    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None,None,None)
        engine.dispose()
        workspace.cleanup()
    def survey(self, **changes):
        payload = dict(title="测试问卷",description="说明",allow_multiple=False,is_anonymous=False,questions=[dict(question_text="单选",question_type="single",options=json.dumps(["选项,一","选项二"],ensure_ascii=False)),dict(question_text="多选",question_type="multiple",options='["甲","乙"]'),dict(question_text="评分",question_type="rating")])
        payload.update(changes)
        response = self.client.post("/api/surveys",json=payload,headers=self.admin)
        self.assertEqual(response.status_code,200,response.text)
        return response.json(),payload
    def answer(self,survey):
        values=["选项,一",'["甲","乙"]',"5"]
        return {"answers":[{"question_id":q["id"],"answer_text":value} for q,value in zip(survey["questions"],values)]}
    def task(self):
        r=self.client.post("/api/file-tasks",headers=self.admin,json={"title":"任务/测试", "deadline":"2099-12-31 23:59:00", "naming_pattern":"{name}_{seq}_{orig}"})
        self.assertEqual(r.status_code,200,r.text)
        return r.json()["id"]
    def upload(self,task,names=("报告.txt",)):
        return self.client.post(f"/api/file-tasks/{task}/submit",headers=self.student,files=[("files",(name,b"test-file-content","text/plain")) for name in names])
    def test_html_allowlist_and_remote_images(self):
        result=clean_html('<p onclick="bad()">hello<script>alert(1)</script><img src="https://tracker.test/a.png"><a href="javascript:alert(1)">bad</a></p>')
        for bad in ['onclick','<script','javascript:','https://tracker']: self.assertNotIn(bad,result)
        self.assertIn('hello',result)
        self.assertEqual(clean_html(''), '')
    def test_unauthenticated_static_and_security_headers(self):
        self.client.cookies.clear()
        r=self.client.get('/static/secret.txt')
        self.assertEqual(r.status_code,401)
        health=self.client.get('/api/health')
        self.assertEqual(health.headers['x-content-type-options'],'nosniff')
        self.assertIn("object-src 'none'",health.headers['content-security-policy'])
    def test_login_cookie_and_account_limit(self):
        r=self.client.post('/api/login',json={"username":"student-test","password":"TestPassword123!"})
        self.assertEqual(r.status_code,200,r.text)
        self.assertIn('HttpOnly',r.headers['set-cookie'])
        for _ in range(8): self.client.post('/api/login',json={"username":"missing-account","password":"wrong"})
        r=self.client.post('/api/login',json={"username":"missing-account","password":"wrong"})
        self.assertEqual(r.status_code,429)
        self.client.cookies.clear()
    def test_survey_membership_complete_answers_and_single_submission(self):
        survey,_=self.survey()
        another,_=self.survey()
        data=self.answer(survey)
        data['answers'][0]['question_id']=another['questions'][0]['id']
        r=self.client.post(f"/api/surveys/{survey['id']}/submit",json=data,headers=self.student)
        self.assertEqual(r.status_code,422,r.text)
        data=self.answer(survey);data['answers'].pop()
        self.assertEqual(self.client.post(f"/api/surveys/{survey['id']}/submit",json=data,headers=self.student).status_code,422)
        data=self.answer(survey)
        self.assertEqual(self.client.post(f"/api/surveys/{survey['id']}/submit",json=data,headers=self.student).status_code,200)
        self.assertEqual(self.client.post(f"/api/surveys/{survey['id']}/submit",json=data,headers=self.student).status_code,409)
        listed=self.client.get('/api/surveys',headers=self.student).json()
        item=next(s for s in listed if s['id']==survey['id'])
        self.assertTrue(item['user_submitted']);self.assertEqual(item['response_count'],1)
    def test_repeat_replaces_answers_and_protects_results(self):
        survey,_=self.survey(allow_multiple=True,is_anonymous=True)
        data=self.answer(survey)
        url=f"/api/surveys/{survey['id']}/submit"
        self.assertEqual(self.client.post(url,json=data,headers=self.student).status_code,200)
        data['answers'][0]['answer_text']='选项二'
        self.assertEqual(self.client.post(url,json=data,headers=self.student).status_code,200)
        with SessionLocal() as db:
            count=db.query(SurveyResponse).join(SurveyQuestion).filter(SurveyQuestion.survey_id==survey['id']).count()
            self.assertEqual(count,3)
        result=self.client.get(f"/api/surveys/{survey['id']}/student-results",headers=self.student).json()
        self.assertEqual(result['questions'][0]['vote_counts'],{'选项二':1})
        self.assertTrue(all(not q['details'] and not q['answers'] for q in result['questions']))
    def test_question_editing_before_and_after_answers(self):
        survey,payload=self.survey()
        payload['questions'][0]['question_text']='修改后的题干'
        r=self.client.put(f"/api/surveys/{survey['id']}",json=payload,headers=self.admin)
        self.assertEqual(r.status_code,200,r.text)
        survey=r.json();self.assertEqual(survey['questions'][0]['question_text'],'修改后的题干')
        self.client.post(f"/api/surveys/{survey['id']}/submit",json=self.answer(survey),headers=self.student)
        payload['title']='仅修改标题'
        r=self.client.put(f"/api/surveys/{survey['id']}",json=payload,headers=self.admin)
        self.assertEqual(r.status_code,200,r.text)
        payload['questions'][0]['question_text']='禁止修改'
        self.assertEqual(self.client.put(f"/api/surveys/{survey['id']}",json=payload,headers=self.admin).status_code,409)
    def test_upload_failure_preserves_previous_files(self):
        task=self.task();self.assertEqual(self.upload(task).status_code,200)
        with SessionLocal() as db:
            old=db.query(FileSubmission).filter_by(task_id=task).one().file_path
        self.assertEqual(self.upload(task,('new.txt','evil.exe')).status_code,400)
        from routers.file_tasks import save_upload
        count=0
        def faulty(file,path):
            nonlocal count
            count+=1
            if count==2: raise OSError('simulated disk failure')
            return save_upload(file,path)
        with patch('routers.file_tasks.save_upload',side_effect=faulty):
            with self.assertRaises(OSError): self.upload(task,('new.txt','second.txt'))
        with SessionLocal() as db:
            rows=db.query(FileSubmission).filter_by(task_id=task).all()
            self.assertEqual(len(rows),1);self.assertEqual(rows[0].file_path,old)
        self.assertTrue((root/'uploads'/old).is_file())
        self.assertEqual(len(list((root/'uploads').glob(f'task_{task}_*'))),1)
    def test_private_file_ownership_and_signed_download(self):
        task=self.task();self.upload(task)
        with SessionLocal() as db: sub=db.query(FileSubmission).filter_by(task_id=task).one();stored=sub.file_path;sid=sub.id
        self.assertEqual(self.client.get('/static/'+stored,headers=self.other).status_code,403)
        self.assertEqual(self.client.get('/static/'+stored,headers=self.student).status_code,200)
        r=self.client.post('/api/transfers',json={'path':f'/api/file-tasks/submissions/{sid}/download'},headers=self.other)
        self.assertEqual(self.client.get(r.json()['url']).status_code,403)
        r=self.client.post('/api/transfers',json={'path':'https://evil.test/download'},headers=self.admin)
        self.assertEqual(r.status_code,400)
        expired=make_ticket(f'/api/file-tasks/submissions/{sid}/download',2,seconds=-1)
        self.assertEqual(self.client.get('/api/transfers/open/'+expired).status_code,401)
    def test_all_zip_range_and_collision_names(self):
        task=self.task();self.upload(task,('同名.txt','同名.txt'))
        path=f'/api/file-tasks/{task}/download-zip?structure=per_student'
        ticket=self.client.post('/api/transfers',json={'path':path},headers=self.admin).json()['url']
        response=self.client.get(ticket)
        self.assertEqual(response.status_code,200,response.text[:100] if response.status_code!=200 else '')
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names=archive.namelist();self.assertEqual(len(names),2);self.assertEqual(len(set(names)),2)
            self.assertTrue(all('..' not in name and not name.startswith('/') for name in names))
        partial=self.client.get(ticket,headers={'Range':'bytes=0-9'})
        self.assertEqual(partial.status_code,206,partial.text)
        self.assertEqual(partial.content,response.content[:10])
        self.assertEqual(partial.headers['etag'],response.headers['etag'])
        self.assertEqual(self.client.get(f'/api/file-tasks/{task}/download-zip?batch=99',headers=self.admin).status_code,404)
    def test_naming_validation(self):
        for value in ['{unknown}','{name.__class__}','{name!r}','{name:10000}']:
            with self.assertRaises(HTTPException): validate_pattern(value)
        self.assertNotIn('/',safe_component('../bad/name'))
        self.assertTrue(safe_component('CON').startswith('_'))
    def test_default_naming_and_missing_files(self):
        task = self.client.post('/api/file-tasks', headers=self.admin, json={'title':'整齐命名', 'deadline':'2099-12-31 23:59:00'}).json()
        self.assertEqual(task['naming_pattern'], '{sid}-{name}-{seq}-{orig}')
        self.upload(task['id'], ('报告.txt', '补充.txt'))
        response = self.client.get(f"/api/file-tasks/{task['id']}/download-zip", headers=self.admin)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ['20260002-张三-01-报告.txt','20260002-张三-02-补充.txt'])
        with SessionLocal() as db:
            row = db.query(FileSubmission).filter_by(task_id=task['id']).first()
            (root/'uploads'/row.file_path).unlink()
        response = self.client.get(f"/api/file-tasks/{task['id']}/download-zip", headers=self.admin)
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertIn('_缺失文件清单.txt', archive.namelist())
            self.assertIn('报告.txt', archive.read('_缺失文件清单.txt').decode('utf-8-sig'))
            self.assertIn('20260002-张三-02-补充.txt', archive.namelist())
        info = self.client.get(f"/api/file-tasks/{task['id']}/download-zip-info", headers=self.admin).json()
        self.assertEqual(info['missing_files'], 1)
        self.assertEqual(self.client.get(f"/api/file-tasks/{task['id']}/download-zip?structure=other", headers=self.admin).status_code, 422)
    def test_frontend_manifest_detects_stale_mount_and_missing_assets(self):
        import hashlib
        from services.buildinfo import inspect_build
        site = root/'frontend-build'; (site/'assets').mkdir(parents=True, exist_ok=True)
        index = b'<script src="/assets/index-abc.js"></script>'
        script = b'console.log("build")'
        (site/'index.html').write_bytes(index)
        (site/'assets'/'index-abc.js').write_bytes(script)
        (site/'manifest.webmanifest').write_text(json.dumps({'name':'sk2441班务'}), encoding='utf-8')
        info = {'version':'2.1.0', 'revision':'test-revision','built_at':'2026-10-18', 'index_sha256':hashlib.sha256(index).hexdigest(), 'assets':{'/assets/index-abc.js':hashlib.sha256(script).hexdigest()}}
        (site/'build-info.json').write_text(json.dumps(info), encoding='utf-8')
        self.assertTrue(inspect_build(site, 'test-revision')['ready'])
        self.assertFalse(inspect_build(site, 'other-revision')['ready'])
        (site/'index.html').write_bytes(b'old mounted frontend')
        self.assertFalse(inspect_build(site, 'test-revision')['ready'])
        (site/'index.html').write_bytes(index)
        (site/'assets'/'index-abc.js').unlink()
        self.assertFalse(inspect_build(site, 'test-revision')['ready'])
        self.assertEqual(self.client.get('/missing.webmanifest').status_code, 404)
    def test_fifty_parallel_reads_do_not_exhaust_workers_or_connections(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=50) as pool:
            responses = list(pool.map(lambda _: self.client.get('/api/file-tasks', headers=self.admin), range(50)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual(engine.pool.checkedout(), 0)
    def test_streaming_response_releases_database_before_download(self):
        from fastapi import FastAPI, Depends
        from starlette.responses import StreamingResponse
        from database import get_db
        from sqlalchemy import text
        site = FastAPI()
        @site.get('/download')
        def stream(db=Depends(get_db, scope='function')):
            db.execute(text('SELECT 1'))
            def chunks():
                self.assertEqual(engine.pool.checkedout(), 0)
                yield b'file-bytes'
            return StreamingResponse(chunks())
        with TestClient(site) as client:
            self.assertEqual(client.get('/download').content, b'file-bytes')
    def test_single_and_student_zip_use_the_same_sequence(self):
        task=self.task();self.upload(task,('第一份.txt','第二份.txt'))
        with SessionLocal() as db:
            subs=db.query(FileSubmission).filter_by(task_id=task).order_by(FileSubmission.id).all()
            second_id=subs[1].id
        response=self.client.get(f'/api/file-tasks/submissions/{second_id}/download',headers=self.student)
        from urllib.parse import unquote
        self.assertIn('_02_第二份.txt',unquote(response.headers['content-disposition']))
        response=self.client.get(f'/api/file-tasks/{task}/students/2/download-zip',headers=self.student)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertTrue(any('_02_第二份.txt' in name for name in archive.namelist()))
    def test_group_zip_resolves_leader_without_a_submission(self):
        from models import GroupProject, GroupAssignment
        with SessionLocal() as db:
            project=GroupProject(name='分组命名测试',admin_id=1,group_names=json.dumps({'1':'组{orig}/A'}))
            db.add(project);db.flush();project_id=project.id
            db.add_all([GroupAssignment(project_id=project_id,group_number=1,student_id=2,role='member'),
                        GroupAssignment(project_id=project_id,group_number=1,student_id=3,role='leader')]);db.commit()
        response=self.client.post('/api/file-tasks',headers=self.admin,json={'title':'小组收集','deadline':'2099-12-31 23:59:00',
            'group_project_id':project_id,'naming_pattern':'{group}-{leader}-{seq}-{orig}'})
        task=response.json()['id'];self.upload(task)
        response=self.client.get(f'/api/file-tasks/{task}/download-zip',headers=self.admin)
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            self.assertEqual(archive.namelist(), ['组{orig}_A-other-test-01-报告.txt'])
    def test_precompressed_public_assets_and_range_fallback(self):
        import gzip
        from fastapi import FastAPI
        from services.staticfiles import CompressedStaticFiles
        assets=root/'assets';assets.mkdir(exist_ok=True)
        body=b'console.log("public asset");'*100
        (assets/'test.js').write_bytes(body)
        (assets/'test.js.gz').write_bytes(gzip.compress(body))
        site=FastAPI();site.mount('/assets',CompressedStaticFiles(directory=assets))
        with TestClient(site) as client:
            response=client.get('/assets/test.js',headers={'Accept-Encoding':'gzip'})
            self.assertEqual(response.content,body)
            self.assertEqual(response.headers['content-encoding'],'gzip')
            self.assertIn('javascript',response.headers['content-type'])
            self.assertEqual(client.get('/assets/test.js',headers={'Accept-Encoding':'gzip;q=0'}).content,body)
            response=client.get('/assets/test.js',headers={'Accept-Encoding':'gzip','Range':'bytes=0-9'})
            self.assertEqual(response.status_code,206);self.assertEqual(response.content,body[:10])
    def test_mime_inline_images_and_large_file_links(self):
        folder=root/'uploads'/'rich';folder.mkdir(exist_ok=True)
        image=folder/('a'*32+'.webp');image.write_bytes(b'small-image')
        large=folder/('b'*32+'.zip');large.write_bytes(b'x'*200000)
        body=f'<p>通知正文</p><img src="/static/rich/{image.name}" alt="图片"><a href="/static/rich/{large.name}">附件</a>'
        message=build_email('sender@example.test','to@example.test','通知',body,50)
        self.assertTrue(any(p.get('Content-ID') for p in message.walk()))
        self.assertIn('/api/transfers/open/',message.get_body(preferencelist=('plain',)).get_content())
        self.assertLess(len(message.as_bytes()),30000)
        response=self.client.post('/api/transfers',json={'path':'/static/rich/'+large.name},headers=self.student)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.client.get(response.json()['url']).content,large.read_bytes())
    def test_qq_sends_segments_and_files_without_cq_injection(self):
        from services.qq import _send_qq_msg
        folder=root/'uploads'/'rich';folder.mkdir(exist_ok=True)
        image=folder/('c'*32+'.webp');image.write_bytes(b'image')
        attachment=folder/('d'*32+'.pdf');attachment.write_bytes(b'pdf')
        body=f'<p>[CQ:at,qq=all] 正文</p><img src="/static/rich/{image.name}"><a href="/static/rich/{attachment.name}">文件</a>'
        with patch.dict(os.environ,QQ_UPLOAD_ROOT='/app/class-uploads'),patch('services.qq._call_qq',return_value={'status':'ok'}) as call:
            result=_send_qq_msg('http://napcat:3001','send_group_msg',{'group_id':123,'message':body})
            self.assertEqual(result['status'],'ok');self.assertEqual(call.call_count,2)
            payload=call.call_args_list[0].args[2]
            self.assertEqual(payload['message'][0]['type'],'text');self.assertEqual(payload['message'][1]['type'],'image')
            self.assertEqual(call.call_args_list[1].args[1],'upload_group_file')

if __name__=='__main__': unittest.main()
