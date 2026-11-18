from backend.rubric import CONDITIONS
import copy,io,json,sqlite3,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib import request,error
from backend.interests import InterestService,topics_from,aggregate,DOMAINS
from backend.service import ServiceError,EvaluationService
from backend.server import handler

TOPICS=[{'id':'a','originalText':'식물 식물 식물 성장과 빛','origin':'original'},{'id':'b','originalText':'온도에 따른 식물 성장','origin':'original'},{'id':'c','originalText':'새로운 센서와 식물 관리','origin':'original'}]
def suggestion():return {'interests':[{'label':'식물 성장','domains':['생물'],'source_topic_ids':['a','a','b'],'reason':'원본의 식물 성장 질문에서 추정'},{'label':'스마트 관찰','domains':['생물','산업 및 에너지'],'source_topic_ids':['b','c'],'reason':'원본의 관리 질문에서 추정'}],'uncertainties':['센서의 용도는 확인 필요']}
def response(data=None):return {'status':'completed','usage':{'input_tokens':10,'output_tokens':20},'output':[{'content':[{'type':'output_text','text':json.dumps(data or suggestion())}]}]}
class Fake:
 def __init__(self,result=None):self.result=result or response();self.calls=[]
 def call(self,path,payload):self.calls.append((path,payload));return copy.deepcopy(self.result)
class Interests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name)
 def test_unique_topic_count_not_word_count(self):
  r=aggregate(TOPICS,**suggestion());self.assertEqual(r['interests'][0]['topic_count'],2);self.assertEqual(r['interests'][0]['ratio'],66.7)
  by_domain={d['domain']:d for d in r['domain_summary']};self.assertEqual(by_domain['생물']['topic_count'],3);self.assertEqual(by_domain['산업 및 에너지']['topic_count'],2);self.assertEqual(by_domain['물리']['topic_count'],0)
 def test_half_up_ratio_matches_browser(self):
  topics=[{'id':str(i),'originalText':'주제 '+str(i),'origin':'original'} for i in range(16)]
  r=aggregate(topics,[{'label':'관심사','domains':['물리'],'reason':'원본에서 추정','source_topic_ids':['0']}],[])
  self.assertEqual(r['interests'][0]['ratio'],6.3)
 def test_unknown_reference_and_generated_rejected(self):
  data=suggestion();data['interests'][0]['source_topic_ids']=['generated-id']
  with self.assertRaises(ServiceError):aggregate(TOPICS,**data)
  with self.assertRaises(ServiceError):topics_from({'topics':TOPICS+[{'id':'g','originalText':'생성된 주제','origin':'generated'}]})
 def test_duplicate_ids_titles_and_oversize(self):
  for topics in [[],TOPICS*2,[{**TOPICS[0],'origin':'generated'}],[{**TOPICS[0],'originalText':'x'*501}],TOPICS+[dict(TOPICS[0],id='extra')]]:
   with self.assertRaises(ServiceError):topics_from({'topics':topics})
 def test_invalid_fields(self):
  for change in [{'domains':[]},{'domains':['의학']},{'label':''},{'source_topic_ids':[]},{'reason':None}]:
   data=suggestion();data['interests'][0].update(change)
   with self.assertRaises(ServiceError):aggregate(TOPICS,**data)
 def test_unassigned_and_uncertain_empty_profile(self):
  r=aggregate(TOPICS,[],['입력만으로 추정 불가']);self.assertEqual(r['unassigned_topic_ids'],['a','b','c'])
  with self.assertRaises(ServiceError):aggregate(TOPICS,[],[])
 def test_ai_cache_schema_privacy_and_usage(self):
  f=Fake();s=InterestService(self.folder,lambda:f);body={'topics':TOPICS,'name':'PRIVATE-NAME','region':'PRIVATE-REGION','generated_topics':[{'text':'DO-NOT-SEND'}]}
  r=s.analyze(body);self.assertFalse(r['confirmed']);self.assertEqual(r['usage']['input_tokens'],10);self.assertTrue(s.analyze(body)['cached']);self.assertEqual(len(f.calls),1)
  payload=f.calls[0][1];self.assertEqual(json.loads(payload['input']),{'topics':TOPICS});self.assertTrue(payload['text']['format']['strict']);self.assertFalse(payload['store'])
 def test_failed_output_never_saved(self):
  for data in [{'status':'incomplete'},{'status':'completed','output':[]},response({'interests':[{**suggestion()['interests'][0],'source_topic_ids':['unknown']}],'uncertainties':[]})]:
   with self.assertRaises(ServiceError):InterestService(self.folder,lambda:Fake(data)).analyze({'topics':TOPICS})
  with sqlite3.connect(self.folder/'interests.sqlite3') as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM interest_versions').fetchone()[0],0)
 def test_manual_confirm_no_provider_and_restart(self):
  s=InterestService(self.folder,lambda:(_ for _ in ()).throw(AssertionError('API not allowed')))
  r=s.confirm({'topics':TOPICS,**suggestion()});self.assertTrue(r['confirmed']);self.assertEqual(r['actor'],'teacher');self.assertIsNone(r['model']);self.assertIsNone(r['usage']);self.assertEqual(InterestService(self.folder).get(r['version']),r)
 def test_manual_edit_versions_and_counts_recomputed(self):
  s=InterestService(self.folder,lambda:Fake());draft=s.analyze({'topics':TOPICS});data=suggestion();data['interests'][0].update(source_topic_ids=['a'],topic_count=999,ratio=100)
  new=s.confirm({'topics':TOPICS,**data,'base_version':draft['version']});self.assertEqual(new['interests'][0]['topic_count'],1);self.assertEqual(new['interests'][0]['ratio'],33.3);self.assertEqual(new['parent_version'],draft['version']);self.assertFalse(s.get(draft['version'])['confirmed'])
 def test_unconfirmed_unknown_and_stale_eval_profiles(self):
  s=InterestService(self.folder,lambda:Fake());draft=s.analyze({'topics':TOPICS})
  for version,ideas in [('missing',[t['originalText'] for t in TOPICS]),(draft['version'],[t['originalText'] for t in TOPICS])]:
   with self.assertRaises(ServiceError):s.confirmed_profile(version,ideas)
  final=s.confirm({'topics':TOPICS,**suggestion()})
  with self.assertRaises(ServiceError):s.confirmed_profile(final['version'],['changed'])
  with self.assertRaises(ServiceError):s.confirm({'topics':[{**TOPICS[0],'originalText':'다른 질문'}],**suggestion(),'base_version':final['version']})
 def test_eval_consumes_trusted_profile_and_cache_changes_on_edit(self):
  s=InterestService(self.folder);one=s.confirm({'topics':TOPICS,**suggestion()});captured=[]
  class Evaluate:
   def call(self,path,payload):
    captured.append(payload);return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':i,**{a:{'score':80,'reason':'확정 관심사 참고'} for a in ['originality','inquiry','feasibility','utility','interest']},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]} for i in range(3)]})}]}]}
  svc=EvaluationService(self.folder,lambda:Evaluate());body={'ideas':[t['originalText'] for t in TOPICS],'grade':'초등 5학년','interest_version':one['version']}
  svc.evaluate(body);context=json.loads(captured[0]['input']);self.assertEqual(context['confirmed_interest_profile']['version'],one['version']);self.assertTrue(svc.evaluate(body)['cached'])
  data=suggestion();data['interests'][0]['source_topic_ids']=['a'];two=s.confirm({'topics':TOPICS,**data,'base_version':one['version']});svc.evaluate({**body,'interest_version':two['version']});self.assertEqual(len(captured),2)

class InterestHTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.service=EvaluationService(Path(self.tmp.name),lambda:Fake());self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.service));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def post(self,path,body,origin=None):
  req=request.Request(self.url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin or self.url})
  with request.urlopen(req) as r:return json.load(r)
 def test_real_http_draft_and_confirm(self):
  draft=self.post('/api/interests/analyze',{'topics':TOPICS});result=self.post('/api/interests/confirm',{'topics':TOPICS,**suggestion(),'base_version':draft['version']});self.assertTrue(result['confirmed']);self.assertEqual(result['total_original_topics'],3)
 def test_cross_origin_blocked(self):
  with self.assertRaises(error.HTTPError) as e:self.post('/api/interests/confirm',{'topics':TOPICS,**suggestion()},'https://untrusted.example')
  self.assertEqual(e.exception.code,403);e.exception.close()
if __name__=='__main__':unittest.main()
