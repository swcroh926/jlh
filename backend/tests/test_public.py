import io,json,tempfile,time,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from backend.public_app import Access,PublicApp
from backend.service import ServiceError

ORIGIN='https://lab.example.org'
CODES={'teacher':'a'*24,'second':'b'*24}
class FakeService:
    index=None
    def __init__(self):self.calls=0
    def evaluate(self,body):self.calls+=1;return {'ok':True}
BODY={'ideas':['식물 성장 비교'],'grade':'초등 5학년','budget':10000,'weeks':4}
class PublicTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
        self.access=Access(self.folder,'s'*40,CODES);self.service=FakeService();self.app=PublicApp(self.service,self.access,ORIGIN)
    def call(self,path,method='GET',body=None,cookie='',origin=ORIGIN,host='lab.example.org'):
        raw=json.dumps(body or {}).encode();status=[];headers=[]
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'HTTP_HOST':host,'HTTP_ORIGIN':origin,'HTTP_COOKIE':cookie,'CONTENT_TYPE':'application/json','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'REMOTE_ADDR':'127.0.0.1'}
        def start(s,h):status.append(int(s.split()[0]));headers.extend(h)
        content=b''.join(self.app(env,start));return status[0],dict(headers),content
    def cookie(self,user='teacher'):return 'jlh_session='+self.access.token(user)
    def test_login_sets_secure_cookie_no_secret_returned(self):
        status,headers,body=self.call('/api/login','POST',{'code':CODES['teacher']})
        self.assertEqual(status,200)
        for flag in ['HttpOnly','Secure','SameSite=Strict']:self.assertIn(flag,headers['Set-Cookie'])
        self.assertEqual(self.access.user(headers['Set-Cookie']),'teacher');self.assertNotIn(CODES['teacher'],body.decode())
    def test_auth_required_and_wrong_code(self):
        self.assertEqual(self.call('/api/evaluate','POST',BODY)[0],401)
        self.assertEqual(self.call('/api/login','POST',{'code':'wrong'})[0],401);self.assertEqual(self.service.calls,0)
    def test_host_and_origin_blocked(self):
        self.assertEqual(self.call('/api/health',host='attacker.org')[0],403)
        self.assertEqual(self.call('/api/evaluate','POST',BODY,self.cookie(),origin='https://attacker.org')[0],403)
        self.assertEqual(self.call('/api/evaluate','POST',BODY,self.cookie(),origin='')[0],403)
    def test_session_tampering_expiry_and_rotation(self):
        token=self.access.token('teacher');self.assertIsNone(self.access.user('jlh_session='+token+'x'))
        with patch('backend.public_app.time.time',return_value=time.time()+43201):self.assertIsNone(self.access.user('jlh_session='+token))
        new=Access(self.folder,'s'*40,{'teacher':'new-code-'+'a'*24});self.assertIsNone(new.user('jlh_session='+token))
    def test_quota_persists_after_restart(self):
        for _ in range(5):self.assertEqual(self.call('/api/evaluate','POST',BODY,self.cookie())[0],200)
        self.assertEqual(self.call('/api/evaluate','POST',BODY,self.cookie())[0],429)
        restarted=Access(self.folder,'s'*40,CODES)
        with self.assertRaises(ServiceError):restarted.consume('evaluate','teacher')
        self.assertEqual(self.service.calls,5)
    def test_invalid_body_does_not_consume_evaluation_quota(self):
        self.assertEqual(self.call('/api/evaluate','POST',{},self.cookie())[0],400)
        with self.access.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM calls WHERE kind='evaluate'").fetchone()[0],0)
    def test_failed_provider_call_consumes_quota(self):
        with patch.object(self.service,'evaluate',side_effect=ServiceError('failure')):
            self.assertEqual(self.call('/api/evaluate','POST',BODY,self.cookie())[0],502)
        with self.access.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM calls WHERE kind='evaluate'").fetchone()[0],1)
    def test_global_hourly_and_daily_quotas(self):
        a=Access(self.folder,'s'*40,CODES,hourly=2,daily=3,user_hourly=5)
        a.consume('evaluate','teacher');a.consume('evaluate','second')
        with self.assertRaises(ServiceError):a.consume('evaluate','teacher')
        a.limits=(10,3,10);a.consume('evaluate','teacher')
        with self.assertRaises(ServiceError):a.consume('evaluate','second')
    def test_concurrent_quota_reservation(self):
        def reserve(_):
            try:self.access.consume('evaluate','teacher');return True
            except ServiceError:return False
        with ThreadPoolExecutor(max_workers=8) as pool:self.assertEqual(sum(pool.map(reserve,range(8))),5)
    def test_login_throttled(self):
        for _ in range(10):self.assertEqual(self.call('/api/login','POST',{'code':'wrong'})[0],401)
        self.assertEqual(self.call('/api/login','POST',{'code':CODES['teacher']})[0],429)
    def test_private_files_never_served(self):
        for name in ['/.env','/.local/evaluations.sqlite3','/backend/service.py','/render.yaml','/../backend/service.py']:
            self.assertEqual(self.call(name)[0],404)
    def test_health_and_logout(self):
        body=json.loads(self.call('/api/health',cookie=self.cookie())[2]);self.assertTrue(body['authenticated']);self.assertFalse(body['development_only'])
        self.assertIn('Max-Age=0',self.call('/api/logout','POST',cookie=self.cookie())[1]['Set-Cookie'])
    def test_bad_startup_configuration(self):
        with self.assertRaises(ValueError):Access(self.folder,'short',CODES)
        with self.assertRaises(ValueError):PublicApp(self.service,self.access,'http://example.org')
if __name__=='__main__':unittest.main()
