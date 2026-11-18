from backend.rubric import CONDITIONS
import copy,json,math,sqlite3,tempfile,threading,unittest
from http.server import ThreadingHTTPServer
from urllib import request
from pathlib import Path
from unittest.mock import patch
from backend.duplicates import DuplicateService,RISK,SIMILAR,NONE,INCOMPLETE,targets_from
from backend.service import EvaluationService,ServiceError,digest,EMBED_MODEL

def row(identity,title,source='서울',kind='학생'):
 return {'id':identity,'uid':source+':'+identity,'source':source,'title':title,'year':'2026','url':('https://www.science.go.kr/' if source=='전국' else 'https://ssei.sen.go.kr/')+'view?id='+identity,'field':'생물','award':'특상','record_type':kind}
ROWS=[row('1','빛의 색에 따른 식물 성장'),row('2','빛의 색에 따른 식물 성장','전국'),row('3','식물 성장과 온도 비교'),row('4','태양 전지의 효율 비교')]
def topics(text='빛의색에 따른 식물 성장'):
 return [{'id':'a','originalText':text,'origin':'original'}]
class Fixture:
 def __init__(self,folder):self.folder=folder;self.data_hash=digest([(r['uid'],r['title']) for r in ROWS]);self.index=None;self.factory=lambda:None
class Duplicates(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name);self.svc=Fixture(self.folder);self.rows=copy.deepcopy(ROWS);self.checker=DuplicateService(self.svc,lambda:self.rows)
 def test_exact_normalized_risk_without_probability_and_no_auto_merge(self):
  r=self.checker.check({'topics':topics()});entry=r['results'][0];self.assertEqual(entry['status'],RISK);self.assertTrue(entry['recommendation_hold']);self.assertFalse(r['semantic_executed']);self.assertEqual(len([m for m in entry['matches'] if m['exact_title']]),2);self.assertNotIn('score',entry['matches'][0]);self.assertIn('제목',entry['limitations'])
 def test_similar_material_different_question_not_high_risk(self):
  r=self.checker.check({'topics':topics('식물 성장과 물의 양 비교')});self.assertEqual(r['results'][0]['status'],SIMILAR);self.assertFalse(r['results'][0]['recommendation_hold'])
 def test_no_match_and_empty_source_failure_distinguished(self):
  r=self.checker.check({'topics':topics('ZZZZQQQQXXXX')});self.assertEqual(r['results'][0]['status'],NONE)
  self.rows.clear();r=self.checker.check({'topics':topics()});self.assertEqual(r['results'][0]['status'],INCOMPLETE);self.assertTrue(r['results'][0]['recommendation_hold'])
 def test_semantic_requires_valid_index_not_silent_fallback(self):
  r=self.checker.check({'topics':topics(),'method':'semantic'});self.assertEqual(r['results'][0]['status'],INCOMPLETE)
  self.assertIn('색인',r['results'][0]['reason'])
 def test_semantic_uses_union_and_never_turns_score_into_probability(self):
  class Embed:
   def embed(self,texts):return [[1.,0.] for t in texts]
  self.svc.factory=Embed;self.svc.index={r['uid']:[1.,0.] for r in ROWS}
  r=self.checker.check({'topics':topics('녹색 광선에서 새싹 자라기'),'method':'semantic'});self.assertTrue(r['semantic_executed']);self.assertEqual(r['results'][0]['status'],SIMILAR)
  self.svc.index['서울:1']=[float('nan'),0.];r=self.checker.check({'topics':topics(),'method':'semantic'});self.assertEqual(r['results'][0]['status'],INCOMPLETE)
 def test_semantic_provider_failure_is_saved_as_incomplete(self):
  class Fail:
   def embed(self,texts):raise ServiceError('테스트 연결 실패')
  self.svc.index={r['uid']:[1.,0.] for r in ROWS};self.svc.factory=Fail
  r=self.checker.check({'topics':topics(),'method':'semantic'});self.assertEqual(r['results'][0]['status'],INCOMPLETE);self.assertEqual(self.checker.get(r['version']),r)
 def test_guidance_excluded_and_bad_source_rejected(self):
  self.rows.append(row('99','공룡 화석 연구',kind='지도논문'));r=self.checker.check({'topics':topics('공룡 화석 연구')});self.assertEqual(r['results'][0]['status'],NONE)
  self.rows[0]['url']='javascript:alert(1)';r=self.checker.check({'topics':topics()});self.assertEqual(r['results'][0]['status'],INCOMPLETE)
 def test_generated_and_original_peer_duplicates_share_candidate_group(self):
  targets=topics()+[{'id':'g','originalText':'빛의 색에 따른 식물 성장','origin':'generated'}]
  r=self.checker.check({'topics':targets});self.assertEqual(r['results'][0]['candidate_group_id'],r['results'][1]['candidate_group_id']);self.assertTrue(r['results'][0]['peer_matches'][0]['exact_title'])
 def test_review_keeps_risk_and_history_but_releases_hold(self):
  r=self.checker.check({'topics':topics()});new=self.checker.review({'version':r['version'],'topic_id':'a','decision':'approved','reason':'원문에서 다른 비교 조건을 확인함'})
  self.assertNotEqual(r['version'],new['version']);self.assertEqual(new['parent_version'],r['version']);self.assertEqual(new['results'][0]['status'],RISK);self.assertFalse(new['results'][0]['recommendation_hold']);self.assertTrue(self.checker.get(r['version'])['results'][0]['recommendation_hold'])
 def test_incomplete_cannot_be_approved(self):
  r=self.checker.check({'topics':topics(),'method':'semantic'})
  with self.assertRaises(ServiceError):self.checker.review({'version':r['version'],'topic_id':'a','decision':'approved','reason':'그냥 승인'})
 def test_data_update_rejects_old_review_and_evaluation(self):
  r=self.checker.check({'topics':topics()});self.rows[0]['title']='제목 변경'
  with self.assertRaises(ServiceError):self.checker.review({'version':r['version'],'topic_id':'a','decision':'approved','reason':'이전 자료 승인'})
  with self.assertRaises(ServiceError):self.checker.evaluation_context(r['version'],[topics()[0]['originalText']])
 def test_confirmed_research_group_keeps_sources_and_invalidates_old_report(self):
  first=self.checker.check({'topics':topics()});fingerprint=first['manifest']['fingerprint'];response=self.checker.group({'fingerprint':fingerprint,'members':['서울:1','전국:2'],'reason':'원문 보고서의 동일 작품임을 확인'})
  self.assertEqual(len(response['groups']),1)
  with self.assertRaises(ServiceError):self.checker.require_current(first)
  r=self.checker.check({'topics':topics()});match=next(m for m in r['results'][0]['matches'] if m['group_confirmed']);self.assertEqual(len(match['sources']),2)
  self.checker.group({'fingerprint':r['manifest']['fingerprint'],'action':'ungroup','group_id':match['study_id'],'reason':'추가 확인으로 다른 연구임을 확인'})
  self.assertEqual(len(self.checker.manifest()['groups']),0)
 def test_details_change_needs_recheck_and_restart_restores(self):
  target=topics();target[0]['method']='빛 조건 변경';r=self.checker.check({'topics':target})
  changed=targets_from({'topics':topics()})
  with self.assertRaises(ServiceError):self.checker.evaluation_context(r['version'],[target[0]['originalText']],changed,['a'])
  restarted=DuplicateService(self.svc,lambda:self.rows);self.assertEqual(restarted.get(r['version']),r)
 def test_input_errors_do_not_create_success(self):
  for body in [{'topics':[]},{'topics':topics()*2},{'topics':topics(),'method':'unknown'},{'topics':[dict(topics()[0],origin='other')]}]:
   with self.assertRaises(ServiceError):self.checker.check(body)
  with self.checker.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM duplicate_versions').fetchone()[0],0)
 def test_selected_subset_can_use_full_report_with_generated_peer(self):
  target=topics()+[{'id':'g','originalText':'태양 전지 효율','origin':'generated'}];r=self.checker.check({'topics':target})
  selected=self.checker.evaluation_context(r['version'],[target[0]['originalText']],targets_from({'topics':target}),['a']);self.assertEqual(len(selected['results']),1)

class EvaluationGating(unittest.TestCase):
 def test_high_score_cannot_override_risk_until_review(self):
  with tempfile.TemporaryDirectory() as d:
   captured=[]
   class Fake:
    def call(self,path,payload):
     captured.append(json.loads(payload['input']));return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':0,**{k:{'score':90,'reason':'검토 필요'} for k in ('originality','inquiry','feasibility','utility','interest')},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]}]})}]}]}
   s=EvaluationService(Path(d),Fake);s.index={r['uid']:[1.,0.] for r in s.rows};check=DuplicateService(s);target=topics(s.rows[0]['title']);r=check.check({'topics':target})
   result=s.evaluate({'ideas':[target[0]['originalText']],'grade':'초등 5학년','duplicate_version':r['version']})
   self.assertEqual(result['score_passed_count'],1);self.assertEqual(result['passed_count'],0);self.assertTrue(result['evaluations'][0]['recommendation_hold']);self.assertIn('duplicate_report',captured[0]);self.assertEqual(result['evaluations'][0]['duplicate_status'],RISK);self.assertEqual(result['search_mode'],'lexical')
   approved=check.review({'version':r['version'],'topic_id':'a','decision':'approved','reason':'서로 다른 조건을 원문에서 확인'})
   result=s.evaluate({'ideas':[target[0]['originalText']],'grade':'초등 5학년','duplicate_version':approved['version']});self.assertEqual(result['passed_count'],1)

class EligibilityDetails(unittest.TestCase):
 def test_equivalent_input_titles_cannot_count_as_two_candidates(self):
  with tempfile.TemporaryDirectory() as folder:
   class Fake:
    def call(self,path,payload):
     n=len(json.loads(payload['input'])['ideas'])
     return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':i,**{k:{'score':90,'reason':'테스트 점수'} for k in ('originality','inquiry','feasibility','utility','interest')},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]} for i in range(n)]})}]}]}
   s=EvaluationService(Path(folder),Fake);checker=DuplicateService(s);title=s.rows[0]['title'];other=' '.join(title)
   target=topics(title)+[{'id':'b','originalText':other,'origin':'generated'}];r=checker.check({'topics':target})
   for identity in ['a','b']:r=checker.review({'version':r['version'],'topic_id':identity,'decision':'approved','reason':'차별성을 검토한 테스트'})
   result=s.evaluate({'ideas':[title,other],'grade':'초등 5학년','duplicate_version':r['version']})
   self.assertEqual(result['score_passed_count'],2);self.assertEqual(result['passed_count'],1)
 def test_incomplete_check_high_score_stays_held(self):
  with tempfile.TemporaryDirectory() as folder:
   class Fake:
    def call(self,path,payload):return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':0,**{k:{'score':90,'reason':'불확실한 테스트'} for k in ('originality','inquiry','feasibility','utility','interest')},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]}]})}]}]}
   s=EvaluationService(Path(folder),Fake);checker=DuplicateService(s);title=s.rows[0]['title'];r=checker.check({'topics':topics(title),'method':'semantic'})
   result=s.evaluate({'ideas':[title],'grade':'초등 5학년','duplicate_version':r['version']});self.assertEqual(result['score_passed_count'],1);self.assertEqual(result['passed_count'],0)
 def test_search_model_version_change_invalidates_old_check(self):
  with tempfile.TemporaryDirectory() as folder:
   svc=Fixture(Path(folder));checker=DuplicateService(svc,lambda:ROWS);r=checker.check({'topics':topics()})
   with patch('backend.duplicates.EMBED_MODEL','a-different-search-model'):
    with self.assertRaises(ServiceError):checker.require_current(r)

class LongDetailsHTTP(unittest.TestCase):
 def test_twenty_topics_with_optional_details_can_reach_evaluation(self):
  from backend.server import handler
  class Fake:
   def call(self,path,payload):
    data=json.loads(payload['input'])
    return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':[{'idea_index':i,**{k:{'score':90,'reason':'테스트 응답'} for k in ('originality','inquiry','feasibility','utility','interest')},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]} for i in range(len(data['ideas']))]})}]}]}
  with tempfile.TemporaryDirectory() as folder:
   svc=EvaluationService(Path(folder),Fake);server=ThreadingHTTPServer(('127.0.0.1',0),handler(svc));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
   def post(path,body):
    req=request.Request(url+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':url})
    with request.urlopen(req) as response:return json.load(response)
   try:
    targets=[{'id':str(i),'originalText':f'ZZZZQQQQXXXX{i}','origin':'original','question':'질'*1000} for i in range(20)]
    report=post('/api/duplicates/check',{'topics':targets});result=post('/api/evaluate',{'ideas':[t['originalText'] for t in targets],'grade':'초등 5학년','duplicate_version':report['version'],'duplicate_topics':targets,'evaluation_topic_ids':[t['id'] for t in targets]})
    self.assertEqual(len(result['evaluations']),20);self.assertEqual(result['search_mode'],'lexical')
   finally:server.shutdown();server.server_close();thread.join()
