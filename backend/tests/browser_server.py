"""Only mocked model calls; real HTTP, SQLite, validation and UI."""
from backend.rubric import CONDITIONS
import os,tempfile,json,argparse
from pathlib import Path
from http.server import ThreadingHTTPServer
from backend.service import EvaluationService
from backend.server import handler
class Fake:
 def call(self,path,payload):
  data=json.loads(payload['input']);name=payload['text']['format']['name']
  if name=='find_interest':
   assert list(data)==['topics']
   topics=data['topics'];ids=[t['id'] for t in topics]
   result={'interests':[{'label':'식물 성장','domains':['생물'],'source_topic_ids':[ids[0],ids[0],ids[1]],'reason':'원본 성장 주제에서 추정'},{'label':'스마트 관찰','domains':['생물','산업 및 에너지'],'source_topic_ids':[ids[1],ids[2]],'reason':'원본 센서 주제에서 추정'}],'uncertainties':['센서의 용도는 확인 필요']}
   if 'MALFORMED' in topics[0]['originalText']:result['interests'][0]['source_topic_ids']=['unknown-id']
  else:
   assert data.get('confirmed_interest_profile',{}).get('version')
   result={'evaluations':[{'idea_index':i,**{k:{'score':80,'reason':'선생님 확정 관심사 참고'} for k in ('originality','inquiry','feasibility','utility','interest')},'execution_checks':{k:{'status':'가능','reason':'테스트 조건 확인'} for k in CONDITIONS},'source_ids':[],'uncertainties':[],'improvements':[]} for i in range(len(data['ideas']))]}
   for e,title in zip(result['evaluations'],data['ideas']):
    if title.startswith('ROUNDING'):
     e['feasibility']['score']=79;e['interest']['score']=81
    elif title.startswith('REVIEW'):e['execution_checks']['safety']={'status':'검토 필요','reason':'테스트: 안전 확인 필요'}
    elif title.startswith('BLOCKED'):e['execution_checks']['equipment']={'status':'불가','reason':'테스트: 필수 장비 없음'}
  return {'status':'completed','usage':{'input_tokens':1,'output_tokens':1},'output':[{'content':[{'type':'output_text','text':json.dumps(result)}]}]}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8014);args=parser.parse_args()
 os.environ['LLM_API_KEY']='local-test-placeholder-not-a-key'
 with tempfile.TemporaryDirectory() as folder:
  svc=EvaluationService(Path(folder),lambda:Fake());server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(svc));print(f'Mocked-provider interest test server on port {args.port}',flush=True)
  try:server.serve_forever()
  except KeyboardInterrupt:pass
  finally:server.server_close()

if __name__=='__main__':main()
