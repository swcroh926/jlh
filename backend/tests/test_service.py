import copy,json,os,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib import request,error
from http.server import ThreadingHTTPServer
from backend.service import *
from backend.server import handler

INPUT={'ideas':['빛의 색에 따른 식물 성장','물의 온도에 따른 변화','종이비행기 모양 비교'],'grade':'초등 5학년','budget':50000,'weeks':4,'threshold':70,'name':'NEVER_SEND_NAME'}
def response(score=80):
 return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':i,**{a:{'score':score,'reason':'조건 확인 필요'} for a in AXES},'source_ids':[],'uncertainties':['제목만 비교함'],'improvements':['조건을 구체화하세요']} for i in range(3)]})}]}]}
class Fake:
 def __init__(self,data=None):self.data=data or response();self.calls=[]
 def call(self,path,payload):self.calls.append((path,payload));return copy.deepcopy(self.data)

class Tests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
 def service(self,fake):return EvaluationService(self.folder,lambda:fake)
 def test_valid_eval_cache_and_name_omission(self):
  fake=Fake();s=self.service(fake);r=s.evaluate(INPUT)
  self.assertEqual(r['passed_count'],3);self.assertEqual(r['next_step'],'select');self.assertEqual(r['top_three_indices'],[0,1,2]);self.assertTrue(s.evaluate(INPUT)['cached']);self.assertEqual(len(fake.calls),1)
  payload=fake.calls[0][1];self.assertNotIn('NEVER_SEND_NAME',json.dumps(payload));self.assertFalse(payload['store']);self.assertTrue(payload['text']['format']['strict'])
 def test_strict_threshold(self):
  r=self.service(Fake(response(70))).evaluate(INPUT);self.assertEqual(r['passed_count'],0);self.assertEqual(r['next_step'],'needs_more_candidates')
 def test_invalid_input_never_calls_provider(self):
  f=Fake();s=self.service(f)
  for updates in [{'ideas':[]},{'budget':-1},{'weeks':float('nan')},{'threshold':True},{'ideas':['a'*501]},{'equipment':1}]:
   with self.assertRaises(ServiceError):s.evaluate({**INPUT,**updates})
  self.assertFalse(f.calls)
 def test_unknown_citation_rejected(self):
  d=response();e=json.loads(d['output'][0]['content'][0]['text']);e['evaluations'][0]['source_ids']=['서울:invented'];d['output'][0]['content'][0]['text']=json.dumps(e)
  with self.assertRaises(ServiceError):self.service(Fake(d)).evaluate(INPUT)
  with sqlite3.connect(self.folder/'evaluations.sqlite3') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM evaluations').fetchone()[0],0)
 def test_incomplete_rejected(self):
  d=response();d['status']='incomplete'
  with self.assertRaises(ServiceError):self.service(Fake(d)).evaluate(INPUT)
 def test_bad_scores_and_duplicate_ids_rejected(self):
  for field,value in [('idea_index',1),('originality',{'score':101,'reason':'bad'})]:
   d=response();e=json.loads(d['output'][0]['content'][0]['text']);e['evaluations'][0][field]=value;d['output'][0]['content'][0]['text']=json.dumps(e)
   with self.assertRaises(ServiceError):self.service(Fake(d)).evaluate(INPUT)
 def test_no_key(self):
  with patch.dict(os.environ,{'LLM_API_KEY':'','OPENAI_API_KEY':''}):
   with self.assertRaises(ServiceError) as e:OpenAI()
   self.assertEqual(e.exception.status,503)
 def test_index_resume_and_semantic_path(self):
  rows=[{'uid':'서울:1','title':'빛','record_type':'학생'},{'uid':'전국:2','title':'온도','record_type':'학생'}]
  class Embed:
   def __init__(self):self.count=0
   def embed(self,texts):self.count+=1;return [[1,0] for _ in texts]
  e=Embed()
  with patch('backend.service.read_data',return_value=rows):
   build_index(e,self.folder);build_index(e,self.folder);self.assertEqual(e.count,1)
   s=EvaluationService(self.folder);self.assertIsNotNone(s.index);self.assertEqual(len(s.retrieve(['빛'],e)[0]),2)
 def test_stale_index_falls_back(self):
  (self.folder/'embeddings.json').write_text(json.dumps({'model':EMBED_MODEL,'fingerprint':'old','vectors':{}}))
  self.assertIsNone(EvaluationService(self.folder).index)
 def test_key_never_returned_in_upstream_error(self):
  with patch.dict(os.environ,{'LLM_API_KEY':'fake-secret'}),patch('backend.service.request.urlopen',side_effect=error.HTTPError('https://api.openai.com',401,'fake-secret',{},None)):
   with self.assertRaises(ServiceError) as e:OpenAI().call('responses',{})
   self.assertNotIn('fake-secret',str(e.exception))

class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.svc=EvaluationService(Path(self.tmp.name),lambda:Fake());self.http=ThreadingHTTPServer(('127.0.0.1',0),handler(self.svc));self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.base=f'http://127.0.0.1:{self.http.server_port}'
 def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
 def test_evaluate_over_http(self):
  req=request.Request(self.base+'/api/evaluate',data=json.dumps(INPUT).encode(),headers={'Content-Type':'application/json','Origin':self.base})
  with request.urlopen(req) as r:self.assertEqual(json.load(r)['passed_count'],3)
 def test_private_files_and_cross_origin_blocked(self):
  for route in ['/.local/evaluations.sqlite3','/.env','/backend/service.py']:
   with self.assertRaises(error.HTTPError) as e:request.urlopen(self.base+route)
   self.assertEqual(e.exception.code,404);e.exception.close()
  req=request.Request(self.base+'/api/evaluate',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://untrusted.example'})
  with self.assertRaises(error.HTTPError) as e:request.urlopen(req)
  self.assertEqual(e.exception.code,403);e.exception.close()
 def test_missing_key_health(self):
  with patch.dict(os.environ,{'LLM_API_KEY':'','OPENAI_API_KEY':''}):
   with request.urlopen(self.base+'/api/health') as r:self.assertFalse(json.load(r)['configured'])
if __name__=='__main__':unittest.main()
