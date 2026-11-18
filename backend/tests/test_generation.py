import json,tempfile,unittest
from pathlib import Path
from backend.service import EvaluationService,ServiceError,AXES
from backend.rubric import CONDITIONS
from backend.generation import GenerationService
from backend.duplicates import DuplicateService
from backend.interests import InterestService

class Generation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);outer=self;self.calls=[];self.bad=False;self.fail_eval=False
  class Fake:
   def call(self,path,payload):
    name=payload['text']['format']['name'];outer.calls.append(name);data=json.loads(payload['input'])
    if name=='create_topic':
     result={'topics':[{'title':('같은 주제' if outer.bad else f'새 질문 {len(outer.calls)}-{i} 광원 조건과 관찰 지표 비교'),'explanation':'원본 비교 조건 보완','question':f'조건 {i} 비교 질문','technique':'측정 조건 변경','experiment_outline':'조건별 반복 측정','original_topic_ids':[data['original_topics'][0]['id']],'improved_axes':['inquiry'],'source_ids':[],'conditions':['장비 확인 필요']} for i in range(data['requested_count'])]}
    else:
     if outer.fail_eval and data.get('original_ideas'):raise ServiceError('테스트 재평가 실패')
     result={'evaluations':[{'idea_index':i,**{a:{'score':85 if data.get('original_ideas') else 60,'reason':'테스트 근거'} for a in AXES},'execution_checks':{k:{'status':'가능','reason':'테스트 조건'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]} for i in range(len(data['ideas']))]}
    return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps(result)}]}]}
  self.s=EvaluationService(Path(self.tmp.name),Fake);self.g=GenerationService(self.s)
 def seed(self,count=2):
  topics=[{'id':str(i),'originalText':f'원본 질문 {i} 식물 조건 비교','origin':'original'} for i in range(count)]
  profile=InterestService(self.s.folder).confirm({'topics':topics,'interests':[],'uncertainties':['테스트 미정']});check=DuplicateService(self.s).check({'topics':topics})
  return self.s.evaluate({'ideas':[t['originalText'] for t in topics],'grade':'초등 5학년','interest_version':profile['version'],'duplicate_version':check['version'],'duplicate_topics':check['topics'],'evaluation_topic_ids':[t['id'] for t in topics]})
 def test_full_workflow_thirty_topics_original_profile_unchanged(self):
  seed=self.seed(20);r=self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'automatic'});self.assertEqual(r['status'],'completed');self.assertEqual(len(r['topics']),10);self.assertEqual(len(r['evaluation']['evaluations']),30);self.assertEqual(r['evaluation']['interest_version'],seed['interest_version']);self.assertEqual(r['evaluation']['passed_count'],30)
 def test_automatic_attempt_cannot_repeat_even_after_result(self):
  seed=self.seed();self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'automatic'});n=len(self.calls)
  with self.assertRaises(ServiceError):self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'automatic'})
  self.assertEqual(n,len(self.calls));self.assertEqual(self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'manual'})['status'],'completed')
 def test_partial_duplicates_are_bounded(self):
  seed=self.seed();self.bad=True;r=self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'automatic'});self.assertEqual(len(r['topics']),1);self.assertEqual(self.calls.count('create_topic'),2);self.assertEqual(r['status'],'completed');self.assertTrue(r['warnings'])
 def test_failed_re_evaluation_preserves_checked_draft(self):
  seed=self.seed();self.fail_eval=True;r=self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'manual'});self.assertEqual(r['status'],'partial');self.assertEqual(r['failed_stage'],'checked');self.assertEqual(len(r['topics']),10);self.assertIn('duplicate_check',r);self.assertNotIn('evaluation',r)
 def test_stale_evidence_rejected_before_provider(self):
  seed=self.seed();self.g.checker.group({'fingerprint':self.g.checker.manifest()['manifest']['fingerprint'],'members':[self.s.rows[0]['uid'],self.s.rows[1]['uid']],'reason':'테스트용 묶음'});n=len(self.calls)
  with self.assertRaises(ServiceError):self.g.run({'evaluation_id':seed['evaluation_id'],'mode':'manual'})
  self.assertEqual(len(self.calls),n)
 def test_unknown_evaluation_and_wrong_mode(self):
  for body in ({'evaluation_id':'bad','mode':'manual'},{'mode':'recursive'}):
   with self.assertRaises(ServiceError):self.g.run(body)
