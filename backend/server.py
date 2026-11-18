"""Loopback-only development server; public deployment needs authentication first."""
import argparse,json,mimetypes,threading,time,os,webbrowser
from pathlib import Path
from collections import deque
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse
from .documents import extract_document
from .interests import InterestService
from .service import ROOT,EvaluationService,ServiceError,key,OpenAI,build_index

FILES={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/model.mjs':'model.mjs','/style.css':'style.css','/search-ui.js':'search-ui.js','/search.mjs':'search.mjs','/eval-ui.js':'eval-ui.js','/input-ui.js':'input-ui.js','/project.mjs':'project.mjs','/interest.mjs':'interest.mjs','/interest-ui.js':'interest-ui.js','/data/awards.json':'data/awards.json'}

def handler(service):
 interests=InterestService(service.folder,service.factory)
 class Handler(BaseHTTPRequestHandler):
  semaphore=threading.BoundedSemaphore(1)
  attempts=deque()
  def log_message(self,*args):pass # Do not log student inputs or upstream errors.
  def reply(self,status,value):
   data=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
  def trusted(self):
   # Localhost only. Check Host and Origin to reject DNS rebinding/cross-site posts.
   host=self.headers.get('Host','');allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
   return host in allowed and (not self.headers.get('Origin') or self.headers['Origin'] in {'http://'+h for h in allowed})
  def do_GET(self):
   if not self.trusted():return self.reply(403,{'error':'접근할 수 없습니다.'})
   path=urlparse(self.path).path
   if path=='/api/health':return self.reply(200,{'configured':bool(key()),'search_mode':'semantic' if service.index else 'lexical','development_only':True,'interests_available':True})
   if path not in FILES:return self.reply(404,{'error':'찾을 수 없습니다.'})
   data=(ROOT/FILES[path]).read_bytes();self.send_response(200);self.send_header('Content-Type',('text/javascript' if path.endswith('.mjs') else mimetypes.guess_type(FILES[path])[0] or 'application/octet-stream')+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-cache');self.end_headers();self.wfile.write(data)
  def do_POST(self):
   if not self.trusted():return self.reply(403,{'error':'접근할 수 없습니다.'})
   if self.path not in ('/api/evaluate','/api/extract-topics','/api/interests/analyze','/api/interests/confirm'):return self.reply(404,{'error':'찾을 수 없습니다.'})
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'error':'JSON 요청이 필요합니다.'})
   try:
    length=int(self.headers.get('Content-Length','0'))
    if not 0<length<=(6_800_000 if self.path=='/api/extract-topics' else 300000 if self.path.startswith('/api/interests/') else 40000):raise ValueError()
    payload=json.loads(self.rfile.read(length))
   except (ValueError,UnicodeError):return self.reply(400,{'error':'요청 크기 또는 형식을 확인해주세요.'})
   if self.path=='/api/extract-topics':
    try:return self.reply(200,extract_document(payload))
    except ServiceError as e:return self.reply(e.status,{'error':str(e)})
    except Exception:return self.reply(500,{'error':'파일을 추출하지 못했습니다.'})
   if self.path=='/api/interests/confirm':
    try:return self.reply(200,interests.confirm(payload))
    except ServiceError as e:return self.reply(e.status,{'error':str(e)})
    except Exception:return self.reply(500,{'error':'관심사를 저장하지 못했습니다.'})
   if not self.semaphore.acquire(blocking=False):return self.reply(429,{'error':'평가가 진행 중입니다. 잠시 후 다시 시도해주세요.'})
   try:
    now=time.monotonic()
    while self.attempts and now-self.attempts[0]>3600:self.attempts.popleft()
    if len(self.attempts)>=10:return self.reply(429,{'error':'개발용 시간당 요청 한도(10회)에 도달했습니다.'})
    self.attempts.append(now)
    self.reply(200,interests.analyze(payload) if self.path=='/api/interests/analyze' else service.evaluate(payload))
   except ServiceError as e:self.reply(e.status,{'error':str(e)})
   except Exception:self.reply(500,{'error':'평가 처리 중 오류가 발생했습니다.'})
   finally:self.semaphore.release()
 return Handler

def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--build-index',action='store_true');p.add_argument('--open-browser',action='store_true',help='서버 준비 후 로컬 브라우저 열기');args=p.parse_args()
 if args.build_index:
  build_index(OpenAI(),Path(os.environ.get('DATA_DIR',str(ROOT/'.local'))));return
 try:server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(EvaluationService()))
 except OSError:p.exit(1,'서버 포트를 열지 못했습니다. 이전 실행 창을 닫거나 다른 포트를 지정해주세요.\n')
 url=f'http://127.0.0.1:{server.server_port}'
 print(f'Local preview: {url}',flush=True)
 print(f'API configured: {bool(key())}. Stop with Ctrl+C.',flush=True)
 timer=None
 if args.open_browser:
  def open_preview():
   try:webbrowser.open(url,new=2)
   except webbrowser.Error:print('브라우저에서 위 주소를 직접 열어주세요.',flush=True)
  timer=threading.Timer(0.3,open_preview);timer.daemon=True;timer.start()
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:
  if timer:timer.cancel()
  server.server_close()
if __name__=='__main__':main()
