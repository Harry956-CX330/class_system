"""Local UI test fixture; temporary database, no SMTP/QQ calls."""
import os
import sys
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

_temp = tempfile.TemporaryDirectory(prefix="class-ui-")
root=Path(_temp.name)
project=Path(__file__).resolve().parents[2]
os.environ.update(DATABASE_URL="sqlite:///"+(root/"test.db").as_posix(),DATA_DIR=str(root),UPLOAD_DIR=str(root/"uploads"),TEMP_DIR=str(root/"archives"),SECRET_KEY="ui-test-secret-"+"z"*40,FRONTEND_DIST=str(project/"client"/"dist"),DOWNLOAD_KIB_PER_SECOND="100000")
sys.path.insert(0,str(project/"backend"))
from database import Base, engine, SessionLocal
from models import User, Notice, FileTask, Survey, SurveyQuestion, Grade
from auth import get_password_hash
from main import app

Base.metadata.create_all(engine)
with SessionLocal() as db:
    hashed=get_password_hash("PreviewOnly123!")
    admin=User(id=1,username="preview-admin",real_name="测试管理员",student_id="A",role="admin",hashed_password=hashed)
    student=User(id=2,username="preview-student",real_name="测试同学",student_id="20260001",role="student",hashed_password=hashed)
    leader=User(id=3,username='preview-leader',real_name='测试班干',student_id='20260002',role='student',is_class_leader=True,hashed_password=hashed)
    db.add_all([admin,student,leader]);db.flush()
    db.add(Grade(student_id=2,score=58,gpa=0.9,semester='第一学期',academic_year='2026-2027'))
    for i in range(3):
        db.add(Notice(title=["本周班会安排与准备事项","课程资料已更新，请及时查阅","新学期班级事务办理提醒"][i],content="<h2>让每一件班级事务都有序进行</h2><p>请同学们查阅本周安排，按时完成学习任务。</p><ul><li>周三下午：班级主题活动</li><li>周五之前：提交课程作业</li></ul><p><strong>如有疑问，请联系班委。</strong></p>",author_id=1))
    db.add(FileTask(title="高等数学 · 第三周实验报告",description="<p>请上传实验报告，<strong>文件名由系统自动整理</strong>。</p>",deadline=datetime(2099,12,31),author_id=1,naming_pattern="{sid}_{name}_{orig}"))
    survey=Survey(title="新学期班级活动意向调查",description="<p>你的意见将帮助我们安排更合适的班级活动。</p>",author_id=1,allow_multiple=True)
    survey.questions=[SurveyQuestion(question_text="你更喜欢哪类班级活动？",question_type="single",options='["户外运动","文化参访","技能分享"]'),SurveyQuestion(question_text="哪些时间段方便参加？",question_type="multiple",options='["周三下午","周六上午","周日下午"]'),SurveyQuestion(question_text="对当前活动安排的满意度",question_type="rating")]
    db.add(survey);db.commit()
if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8765,log_level="warning")
