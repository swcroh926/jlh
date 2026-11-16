"""Single-instance WSGI beta deployment with access-code sessions and durable limits."""
import base64,hashlib,hmac,json,os,re,secrets,sqlite3,time,threading
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import urlparse
from .service import ROOT,EvaluationService,ServiceError,key,validate
from .server import FILES
import mimetypes

class Access:
    def __init__(self,folder,secret,codes,hourly=10,daily=30,user_hourly=5):
        if len(secret)<32 or not codes or any(not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',u) or not isinstance(c,str) or len(c)<16 for u,c in codes.items()):
            raise ValueError('SESSION_SECRET(32자 이상)와 BETA_ACCESS_CODES(JSON, 사용자별 16자 이상 코드)를 설정하세요.')
        self.secret=secret.encode();self.codes=codes;self.limits=(hourly,daily,user_hourly)
        self.database=folder/'access.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS calls (at REAL, kind TEXT, subject TEXT, units INTEGER)')
            db.execute('CREATE INDEX IF NOT EXISTS calls_time ON calls(at)')
    def connect(self):return sqlite3.connect(self.database,timeout=15)
    def sign(self,text):return hmac.new(self.secret,text.encode(),hashlib.sha256).hexdigest()
    def identity(self,code):
        found=None
        for user,expected in self.codes.items():
            if hmac.compare_digest(code.encode(),expected.encode()):found=user
        return found
    def token(self,user):
        # Code rotation invalidates previously issued sessions.
        data=json.dumps({'user':user,'expires':int(time.time())+43200,'version':self.sign(self.codes[user]),'nonce':secrets.token_hex(8)},separators=(',',':'))
        encoded=base64.urlsafe_b64encode(data.encode()).decode().rstrip('=')
        return encoded+'.'+self.sign(encoded)
    def user(self,cookie):
        try:
            parsed=SimpleCookie();parsed.load(cookie);token=parsed['jlh_session'].value
            payload,signature=token.split('.')
            if not hmac.compare_digest(self.sign(payload),signature):return None
            data=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
            user=data['user']
            if user not in self.codes or data['expires']<=time.time() or not hmac.compare_digest(data['version'],self.sign(self.codes[user])):return None
            return user
        except (ValueError,KeyError,TypeError,AttributeError):return None
    def consume(self,kind,subject,units=1):
        now=time.time()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM calls WHERE at<?',(now-86400,))
            if kind=='login':
                # Global + per-address login attempts; address retained only as keyed hash.
                global_count=db.execute("SELECT COUNT(*) FROM calls WHERE kind='login' AND at>?",(now-3600,)).fetchone()[0]
                user_count=db.execute("SELECT COUNT(*) FROM calls WHERE kind='login' AND subject=? AND at>?",(subject,now-3600)).fetchone()[0]
                allowed=global_count<100 and user_count<10
            else:
                hourly=db.execute("SELECT COUNT(*) FROM calls WHERE kind='evaluate' AND at>?",(now-3600,)).fetchone()[0]
                daily=db.execute("SELECT COUNT(*) FROM calls WHERE kind='evaluate'",()).fetchone()[0]
                own=db.execute("SELECT COUNT(*) FROM calls WHERE kind='evaluate' AND subject=? AND at>?",(subject,now-3600)).fetchone()[0]
                ideas=db.execute("SELECT COALESCE(SUM(units),0) FROM calls WHERE kind='evaluate'",()).fetchone()[0]
                allowed=hourly<self.limits[0] and daily<self.limits[1] and own<self.limits[2] and ideas+units<=200
            if not allowed:raise ServiceError('사용 한도에 도달했습니다. 나중에 다시 시도해주세요.',429)
            db.execute('INSERT INTO calls VALUES (?,?,?,?)',(now,kind,subject,units))

class PublicApp:
    def __init__(self,service,access,origin):
        parsed=urlparse(origin)
        if parsed.scheme!='https' or not parsed.netloc or parsed.path not in ('','/') or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('PUBLIC_ORIGIN에 https://서비스.onrender.com 형식의 주소를 설정하세요.')
        self.origin=origin.rstrip('/');self.host=parsed.netloc;self.service=service;self.access=access
        self.busy=threading.BoundedSemaphore(1)
    def __call__(self,environ,start_response):
        def reply(status,value,cookie=None):
            body=json.dumps(value,ensure_ascii=False).encode()
            return finish(status,body,'application/json; charset=utf-8',cookie)
        def finish(status,body,content_type,cookie=None):
            headers=[('Content-Type',content_type),('Content-Length',str(len(body))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','same-origin'),('X-Frame-Options','DENY')]
            if cookie:headers.append(('Set-Cookie',cookie))
            start_response(f'{status} '+{200:'OK',400:'Bad Request',401:'Unauthorized',403:'Forbidden',404:'Not Found',405:'Method Not Allowed',413:'Content Too Large',415:'Unsupported Media Type',429:'Too Many Requests',500:'Internal Server Error',502:'Bad Gateway',503:'Service Unavailable'}.get(status,'Error'),headers)
            return [body]
        path=environ.get('PATH_INFO','/');method=environ.get('REQUEST_METHOD','GET')
        if environ.get('HTTP_HOST')!=self.host:return reply(403,{'error':'접근할 수 없습니다.'})
        user=self.access.user(environ.get('HTTP_COOKIE',''))
        if method=='GET':
            if path=='/api/health':return reply(200,{'configured':bool(key()),'authenticated':bool(user),'auth_required':True,'search_mode':'semantic' if self.service.index else 'lexical','development_only':False})
            if path not in FILES:return reply(404,{'error':'찾을 수 없습니다.'})
            file=ROOT/FILES[path]
            return finish(200,file.read_bytes(),('text/javascript' if file.suffix in ('.mjs','.js') else mimetypes.guess_type(file.name)[0] or 'application/octet-stream')+'; charset=utf-8')
        if method!='POST':return reply(405,{'error':'지원하지 않는 요청입니다.'})
        if environ.get('HTTP_ORIGIN')!=self.origin:return reply(403,{'error':'사이트 주소를 확인해주세요.'})
        if path not in ('/api/login','/api/logout','/api/evaluate'):return reply(404,{'error':'찾을 수 없습니다.'})
        if path=='/api/evaluate' and not user:return reply(401,{'error':'먼저 접근 코드로 연결해주세요.'})
        if path=='/api/logout':return reply(200,{'ok':True},'jlh_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0')
        if environ.get('CONTENT_TYPE','').split(';')[0]!='application/json':return reply(415,{'error':'JSON 요청이 필요합니다.'})
        try:
            length=int(environ.get('CONTENT_LENGTH','0'))
            if not 0<length<=40000:return reply(413,{'error':'요청 크기를 확인해주세요.'})
            payload=json.loads(environ['wsgi.input'].read(length))
            if not isinstance(payload,dict):raise ValueError()
        except (ValueError,UnicodeError):return reply(400,{'error':'요청 형식을 확인해주세요.'})
        try:
            if path=='/api/login':
                self.access.consume('login',self.access.sign(environ.get('REMOTE_ADDR','unknown')))
                code=payload.get('code','')
                if not isinstance(code,str) or len(code)>256:return reply(400,{'error':'접근 코드를 확인해주세요.'})
                identity=self.access.identity(code)
                if not identity:return reply(401,{'error':'접근 코드가 올바르지 않습니다.'})
                return reply(200,{'ok':True},f'jlh_session={self.access.token(identity)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=43200')
            validate(payload)
            if not self.busy.acquire(blocking=False):return reply(429,{'error':'평가가 진행 중입니다. 잠시 후 다시 시도해주세요.'})
            try:
                # Reservations persist across failures/restarts; never auto retry paid calls.
                self.access.consume('evaluate',user,len(payload['ideas']))
                return reply(200,self.service.evaluate(payload))
            finally:self.busy.release()
        except ServiceError as e:return reply(e.status,{'error':str(e)})
        except Exception:return reply(500,{'error':'서버 처리 중 오류가 발생했습니다.'})

def create_app():
    folder=Path(os.environ.get('DATA_DIR',str(ROOT/'.local')));folder.mkdir(parents=True,exist_ok=True)
    codes=json.loads(os.environ.get('BETA_ACCESS_CODES','{}'))
    access=Access(folder,os.environ.get('SESSION_SECRET',''),codes)
    return PublicApp(EvaluationService(folder),access,os.environ.get('PUBLIC_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL',''))
