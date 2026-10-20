"""Bounded single-worker traffic defense, incident history and notification admission."""
import asyncio
import ipaddress
import json
import threading
import time
from collections import OrderedDict, deque
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, ConfigDict, Field
from services.private_settings import read_settings, write_settings, settings_lock

class DefenseSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool = True
    alerts_enabled: bool = True
    ip_per_10_seconds: int = Field(default=300, ge=150, le=3000)
    ip_per_minute: int = Field(default=1800, ge=600, le=12000)
    global_per_10_seconds: int = Field(default=1500, ge=600, le=12000)
    login_per_minute: int = Field(default=120, ge=60, le=600)
    login_failures_per_minute: int = Field(default=30, ge=15, le=300)
    block_seconds: int = Field(default=300, ge=60, le=1800)
    alert_cooldown_seconds: int = Field(default=300, ge=60, le=3600)


def timestamp():
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')

class TrafficMonitor:
    def __init__(self, clock=time.monotonic):
        self.clock=clock; self.lock=threading.RLock(); self.peers=OrderedDict(); self.events=deque(maxlen=100)
        self.seconds=deque(maxlen=61); self.settings=DefenseSettings().model_dump();self.settings_at=-100
        self.total=0;self.rejected=0;self.inflight=0;self.started=clock();self.global_until=0
        self.next_alert=0;self.pending=None;self.alerts=deque(maxlen=30);self.sequence=0
        self.last_save=-100;self.last_incident=-100;self.dirty=False

    def refresh(self):
        now=self.clock()
        if now-self.settings_at<10:return
        try:
            with settings_lock: value=read_settings('defense-settings.json',{})
            settings=DefenseSettings.model_validate(value).model_dump()
            with self.lock:self.settings=settings
        except (OSError,ValueError,TypeError):pass
        self.settings_at=now

    @staticmethod
    def bucket(rows, now):
        second=int(now)
        while rows and second-rows[0][0]>=60:rows.popleft()
        if not rows or rows[-1][0]!=second:rows.append([second,0,0,0])
        return rows[-1]

    @staticmethod
    def count(rows, now, seconds, index=1):
        return sum(row[index] for row in rows if int(now)-row[0]<seconds)

    def incident(self, peer, reason, path, action):
        now=self.clock()
        self.last_incident=now
        self.sequence+=1
        event={'id':self.sequence,'time':timestamp(),'peer':peer,'reason':reason,'path':path[:120],
               'action':action,'blocked_until':None,'count':1}
        if self.events and self.events[-1]['peer']==peer and self.events[-1]['reason']==reason and now-self.events[-1]['_at']<60:
            event=self.events[-1];event['count']+=1;event['action']=action
        else:
            event['_at']=now;self.events.append(event)
        self.dirty=True
        if self.settings['alerts_enabled']:
            if self.pending:
                self.pending['incidents']+=1
                if self.pending['event']['id']==event['id']:
                    self.pending['event']={k:v for k,v in event.items() if k!='_at'}
            elif now>=self.next_alert:
                self.pending={'event':{k:v for k,v in event.items() if k!='_at'},'incidents':1,'attempts':0,
                              'retry_at':now,'channels':{}}
                self.next_alert=now+self.settings['alert_cooldown_seconds']

    def enter(self, peer, path):
        self.refresh();now=self.clock()
        try: peer=str(ipaddress.ip_address(peer))
        except ValueError:peer='unknown'
        with self.lock:
            row=self.bucket(self.seconds,now);row[1]+=1;self.total+=1
            state=self.peers.pop(peer,None) or {'seconds':deque(maxlen=61),'until':0,'violations':deque(maxlen=3),'last':now}
            self.peers[peer]=state;state['last']=now
            while len(self.peers)>4096:self.peers.popitem(last=False)
            per=self.bucket(state['seconds'],now);per[1]+=1
            settings=self.settings; reason=None; retry=0;action='限速'
            if settings['enabled']:
                if state['until']>now:
                    retry=state['until']-now
                elif now<self.global_until:retry=self.global_until-now
                elif self.count(state['seconds'],now,10)>settings['ip_per_10_seconds']:
                    reason='同一来源短时间请求过多';retry=10
                elif self.count(state['seconds'],now,60)>settings['ip_per_minute']:
                    reason='同一来源每分钟请求超限';retry=60
                elif self.count(self.seconds,now,10)>settings['global_per_10_seconds']:
                    reason='全站请求突增';retry=5;self.global_until=now+5
                elif path in {'/api/login','/api/password-reset'}:
                    per[3]+=1
                    if self.count(state['seconds'],now,60,3)>settings['login_per_minute']:
                        reason='登录或密码重置请求过多';retry=60
                if reason:
                    # A single burst gets 429 first. Repeated violations block the source.
                    state['violations'].append(now)
                    if len(state['violations'])==3 and now-state['violations'][0]<10 and reason!='全站请求突增':
                        state['until']=now+settings['block_seconds'];retry=settings['block_seconds'];action='临时封禁来源'
                    self.incident(peer,reason,path,action)
            if retry:
                row[2]+=1;per[2]+=1;self.rejected+=1
            else:self.inflight+=1
            return max(1,int(retry)+1) if retry else 0

    def leave(self,peer,path,status):
        now=self.clock()
        try:peer=str(ipaddress.ip_address(peer))
        except ValueError:peer='unknown'
        with self.lock:
            self.inflight=max(0,self.inflight-1)
            if path in {'/api/login','/api/password-reset'} and status in {400,401,403,429}:
                state=self.peers.get(peer)
                if state:
                    failures=state.setdefault('failures',deque(maxlen=301));failures.append(now)
                    while failures and now-failures[0]>=60:failures.popleft()
                    if self.settings['enabled'] and len(failures)>=self.settings['login_failures_per_minute'] and state['until']<=now:
                        state['until']=now+self.settings['block_seconds']
                        self.incident(peer,'登录失败频繁，疑似口令尝试',path,'临时封禁来源')

    def snapshot(self):
        self.refresh();now=self.clock()
        with self.lock:
            return {'uptime_seconds':int(now-self.started),'total_requests':self.total,'rejected_requests':self.rejected,
                'requests_last_minute':self.count(self.seconds,now,60),'rejected_last_minute':self.count(self.seconds,now,60,2),
                'inflight_requests':self.inflight,'tracked_sources':len(self.peers),
                'blocked_sources':[{'peer':peer,'remaining_seconds':int(state['until']-now)} for peer,state in self.peers.items() if state['until']>now][:100],
                'events':[{k:v for k,v in event.items() if k!='_at'} for event in reversed(self.events)],
                'alerts':json.loads(json.dumps(list(reversed(self.alerts)))),'pending_alert':bool(self.pending),'settings':dict(self.settings)}

    def flush(self):
        """Run off the request loop, at most one bounded batch with two channel workers."""
        now=self.clock()
        with self.lock:
            if not self.settings['alerts_enabled']: self.pending=None
            pending=self.pending if self.pending and now>=self.pending['retry_at'] else None
            if pending:pending['attempts']+=1
        if pending:
            from services.security_alerts import deliver_security_alert
            try:
                result=deliver_security_alert(pending)
            except Exception:
                # Failed preparation must not retry forever or disclose configuration secrets.
                result={name:{'sent':0,'failed':0,'missing':0,'state':'告警准备失败，请检查服务配置','retry':True}
                        for name in ('email','qq') if not pending['channels'].get(name) or pending['channels'][name].get('retry')}
            with self.lock:
                pending['channels'].update(result)
                if any(row.get('retry') for row in result.values()) and pending['attempts']<3:
                    pending['retry_at']=self.clock()+15
                else:
                    self.alerts.append({'time':timestamp(),'event':pending['event']['reason'],'incidents':pending['incidents'],
                                        'channels':{name:{key:value for key,value in data.items() if not key.startswith('_')} for name,data in pending['channels'].items()}})
                    self.pending=None;self.dirty=True
        with self.lock:
            if self.dirty and now-self.last_save>=10:
                history={'events':[{k:v for k,v in event.items() if k!='_at'} for event in self.events], 'alerts':list(self.alerts)}
                self.last_save=now;self.dirty=False
            else:history=None
        if history is not None:
            try:
                with settings_lock:write_settings('security-history.json',history)
            except OSError:pass

    def restore(self):
        try:
            with settings_lock:history=read_settings('security-history.json',{})
            with self.lock:
                for event in history.get('events',[])[-100:]:
                    self.events.append({**event,'_at':-1000});self.sequence=max(self.sequence,int(event.get('id',0)))
                self.alerts.extend(history.get('alerts',[])[-30:])
        except (OSError,ValueError,TypeError,AttributeError):pass

monitor=TrafficMonitor()

async def run_monitor():
    import os
    if os.environ.get('SECURITY_ALERT_DELIVERY','1')=='0':return
    monitor.restore()
    while True:
        try:await asyncio.to_thread(monitor.flush)
        except Exception:
            # Never leak SMTP credentials/provider details to logs or block requests.
            pass
        await asyncio.sleep(1)
