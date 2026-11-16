"""Normalize a collected snapshot; preserve classification provenance."""
import json,sys
from collections import Counter
from pathlib import Path

def normalize(records):
 output=[];seen=set()
 for r in records:
  key=(r['source'],r['id'])
  if key in seen:raise ValueError(f'Duplicate identity: {key}')
  seen.add(key)
  row={k:r.get(k,'') for k in ['source','id','title','year','field','award','record_type','url','evidence','collected_at']}
  row['raw_record_type']=r['record_type']
  if r['record_type']=='지도논문' or r['title'].lstrip().startswith('(지도논문)'):
   row.update(record_type='지도논문',classification_basis='목록/제목 표기')
  elif r['source']=='전국' and r['record_type']=='미분류':
   row.update(record_type='학생',classification_basis='사용자 확인: 전국 미분류는 학생 작품')
  elif r['record_type']=='학생':row['classification_basis']='목록 표기'
  else:row.update(record_type='확인 필요',classification_basis='원본 자료 유형 확인 필요')
  output.append(row)
 return {'metadata':{'total':len(output),'sources':dict(Counter(r['source'] for r in output)),
  'types':dict(Counter(r['record_type'] for r in output)),
  'coverage':'업로드된 수집 범위이며 전체 게시판 수집 완료를 의미하지 않습니다.'},'records':output}
if __name__=='__main__':
 result=normalize(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig')))
 Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')))
 print(result['metadata'])
