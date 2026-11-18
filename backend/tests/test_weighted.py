import json,sqlite3,tempfile,unittest
from pathlib import Path
from backend.service import EvaluationService,ServiceError,AXES,RUBRIC
from backend.rubric import CONDITIONS,WEIGHTS


def entry(index=0,score=80):
 return {'idea_index':index,**{a:{'score':score,'reason':'검증 근거'} for a in AXES},'execution_checks':{k:{'status':'가능','reason':'조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]}

class WeightedEvaluation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.entries=[entry()];self.calls=0
  outer=self
  class Fake:
   def call(self,path,payload):
    outer.calls+=1
    return {'status':'completed','output':[{'content':[{'type':'output_text','text':json.dumps({'evaluations':outer.entries})}]}]}
  self.svc=EvaluationService(Path(self.tmp.name),Fake)
 def evaluate(self,**extra):return self.svc.evaluate({'ideas':['검증 질문 '+str(i) for i in range(len(self.entries))],'grade':'초등 5학년',**extra})
 def test_weights_and_eighty_is_inclusive_even_legacy_threshold(self):
  result=self.evaluate(threshold=99)
  self.assertEqual(result['weights'],WEIGHTS);self.assertEqual(result['threshold'],80);self.assertEqual(result['evaluations'][0]['weighted_total'],80);self.assertEqual(result['passed_count'],1)
 def test_display_rounding_cannot_pass_79_95(self):
  self.entries[0]['feasibility']['score']=79;self.entries[0]['interest']['score']=81
  result=self.evaluate(threshold=0);e=result['evaluations'][0]
  self.assertEqual(e['weighted_total'],79.95);self.assertEqual(e['average'],80.0);self.assertFalse(e['passed']);self.assertEqual(result['passed_count'],0)
 def test_worst_condition_controls_eligibility_without_changing_total(self):
  self.entries=[entry(i,95) for i in range(3)]
  self.entries[1]['execution_checks']['safety']['status']='검토 필요';self.entries[2]['execution_checks']['budget']['status']='불가'
  result=self.evaluate();self.assertEqual([e['execution_status'] for e in result['evaluations']],['가능','검토 필요','불가']);self.assertEqual(result['score_passed_count'],3);self.assertEqual(result['passed_count'],1);self.assertEqual(result['top_three_indices'],[0]);self.assertEqual(result['next_step'],'needs_more_candidates')
 def test_rank_uses_unrounded_total_and_stable_input_order(self):
  self.entries=[entry(i) for i in range(4)]
  self.entries[0]['feasibility']['score']=81;self.entries[0]['interest']['score']=79
  self.entries[1]['interest']['score']=81
  result=self.evaluate();self.assertEqual(result['top_three_indices'],[1,0,2]);self.assertEqual(result['next_step'],'select')
 def test_incomplete_execution_and_old_model_response_never_saved(self):
  for change in ['missing','status','empty','old_axis','bool_index']:
   self.entries=[entry()]
   if change=='missing':del self.entries[0]['execution_checks']['time']
   elif change=='status':self.entries[0]['execution_checks']['time']['status']='아마 가능'
   elif change=='empty':self.entries[0]['execution_checks']['time']['reason']=' '
   elif change=='old_axis':self.entries[0]['award_fit']=self.entries[0].pop('inquiry')
   else:self.entries[0]['idea_index']=False
   with self.assertRaises(ServiceError):self.evaluate()
  with sqlite3.connect(self.svc.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM evaluations').fetchone()[0],0)
 def test_old_rubric_cache_is_not_reused_and_new_cache_is_reused(self):
  from unittest.mock import patch
  with patch('backend.service.RUBRIC','old-rubric'):self.evaluate()
  result=self.evaluate();self.assertFalse(result['cached']);self.assertEqual(result['rubric_version'],RUBRIC);self.assertTrue(self.evaluate()['cached']);self.assertEqual(self.calls,2)
