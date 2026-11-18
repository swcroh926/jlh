"""Check_Duplicate: evidence-limited title comparisons, explicit review, version history."""
import copy,difflib,json,math,re,sqlite3,time,unicodedata,uuid
from urllib.parse import urlparse
from .service import ServiceError,digest,read_data,cosine,EMBED_MODEL

CRITERIA='duplicate-title-risk-v1'
SEARCH_VERSION='nfkc-dice-semantic-union-v1'
RISK='중복 위험';SIMILAR='유사 연구 있음';NONE='현재 자료에서 뚜렷한 유사 연구 미발견';INCOMPLETE='검사 미완료'
LIMITATION='제목 수준 비교입니다. 실험 방법·결과·표절을 확정하지 않으며 미발견이 독창성을 보장하지 않습니다.'

def normalize(text):return ''.join(c for c in unicodedata.normalize('NFKC',text).casefold() if c.isalnum())
def grams(text):return {text[i:i+2] for i in range(len(text)-1)}
def lexical(a,b):
    ga,gb=grams(a),grams(b);common=len(ga&gb)
    return 2*common/max(1,len(ga)+len(gb)),common

def targets_from(body):
    if not isinstance(body,dict):raise ServiceError('검사 요청 형식이 올바르지 않습니다.',400)
    targets=body.get('topics')
    if not isinstance(targets,list) or not 1<=len(targets)<=30:raise ServiceError('검사할 주제는 1~30개여야 합니다.',400)
    clean=[];seen=set()
    for t in targets:
        if not isinstance(t,dict):raise ServiceError('검사 주제 형식이 올바르지 않습니다.',400)
        identity,text=t.get('id'),t.get('originalText');origin=t.get('origin')
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9:_-]{1,100}',identity) or identity in seen:raise ServiceError('검사 주제 ID를 확인해주세요.',400)
        if not isinstance(text,str) or not 2<=len(text.strip())<=500 or len(text)>1000 or not normalize(text):raise ServiceError('검사 주제는 유효한 제목으로 입력해주세요.',400)
        if origin not in ('original','generated'):raise ServiceError('원본·생성 주제 구분을 확인해주세요.',400)
        item={'id':identity,'originalText':text,'origin':origin}
        for field in ('question','target','method','measurement'):
            value=t.get(field,'')
            if not isinstance(value,str) or len(value)>1000:raise ServiceError('주제 보완 정보는 각각 1000자 이내여야 합니다.',400)
            item[field]=value.strip()
        seen.add(identity);clean.append(item)
    return clean

class DuplicateService:
    def __init__(self,service,loader=read_data):
        self.service=service;self.folder=service.folder;self.loader=loader;self.database=self.folder/'duplicates.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS duplicate_versions (version TEXT PRIMARY KEY, created REAL, result TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS research_groups (version TEXT PRIMARY KEY, active INTEGER, members TEXT, reason TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS group_events (version TEXT PRIMARY KEY, created REAL, action TEXT, payload TEXT)')
    def connect(self):return sqlite3.connect(self.database,timeout=15)
    def snapshot(self):
        rows=self.loader();known={}
        if not isinstance(rows,list) or not rows:raise ServiceError('검색할 자료를 읽지 못했습니다. 데이터 파일을 확인해주세요.',503)
        for row in rows:
            if not isinstance(row,dict):raise ServiceError('검색 자료 형식이 올바르지 않습니다.',503)
            if row.get('record_type')=='지도논문':continue
            if not all(isinstance(row.get(k),str) and row[k] for k in ('source','id','title','year','url')):raise ServiceError('자료에 제목·출처 정보가 누락돼 검사를 완료할 수 없습니다.',503)
            link=urlparse(row['url'])
            if link.scheme!='https' or link.hostname not in ('www.science.go.kr','ssei.sen.go.kr','www.gise.kr','gice.gen.go.kr','aicei.ice.go.kr','gnse.gne.go.kr','www.gbe.kr','org.jje.go.kr'):raise ServiceError('출처 주소를 검증하지 못했습니다.',503)
            record={k:row.get(k,'') for k in ('source','id','title','year','field','award','record_type','url')};record['uid']=row['source']+':'+row['id']
            if record['uid'] in known:raise ServiceError('검색 자료의 고유 ID가 중복됐습니다.',503)
            known[record['uid']]=record
        if not known:raise ServiceError('지도논문을 제외한 검색 자료가 없습니다.',503)
        with self.connect() as db:groups=[{'id':v,'members':json.loads(m),'reason':r} for v,m,r in db.execute('SELECT version,members,reason FROM research_groups WHERE active=1 ORDER BY version')]
        groups=[g for g in groups if all(uid in known for uid in g['members'])]
        canonical=sorted(known.values(),key=lambda r:r['uid']);data_version=digest(canonical)
        manifest={'data_version':data_version,'criteria_version':CRITERIA,'search_version':SEARCH_VERSION,'embedding_model':EMBED_MODEL,'groups_version':digest(groups),'record_count':len(known),'sources':{source:sum(r['source']==source for r in canonical) for source in sorted({r['source'] for r in canonical})},'guidance_excluded':True}
        manifest['fingerprint']=digest(manifest)
        return known,groups,manifest
    def manifest(self):
        known,groups,manifest=self.snapshot()
        compatible=digest([(r['uid'],r['title']) for r in known.values()])==self.service.data_hash
        return {'manifest':manifest,'groups':groups,'semantic_available':bool(self.service.index) and compatible}
    def get(self,version):
        if not isinstance(version,str) or not 1<=len(version)<=100:raise ServiceError('검사 버전 형식을 확인해주세요.',400)
        with self.connect() as db:row=db.execute('SELECT result FROM duplicate_versions WHERE version=?',(version,)).fetchone()
        if not row:raise ServiceError('저장된 검사를 찾지 못했습니다. 다시 검사해주세요.',400)
        return json.loads(row[0])
    def save(self,result):
        result['version']=str(uuid.uuid4());result['created_at']=time.time()
        with self.connect() as db:db.execute('INSERT INTO duplicate_versions VALUES (?,?,?)',(result['version'],result['created_at'],json.dumps(result,ensure_ascii=False)))
        return result
    def require_current(self,result):
        if result['manifest']['fingerprint']!=self.snapshot()[2]['fingerprint']:raise ServiceError('자료·검색 기준·연구 묶음이 변경됐습니다. 다시 검사해주세요.',409)
    def group(self,body):
        if not isinstance(body,dict):raise ServiceError('연구 묶음 요청을 확인해주세요.',400)
        known,groups,manifest=self.snapshot()
        if body.get('fingerprint')!=manifest['fingerprint']:raise ServiceError('자료가 변경됐습니다. 화면을 다시 확인해주세요.',409)
        reason=body.get('reason','');action=body.get('action','group')
        if not isinstance(reason,str) or not 1<=len(reason.strip())<=1000:raise ServiceError('같은 연구임을 확인한 근거나 해제 이유를 입력해주세요.',400)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            live=[{'id':v,'members':json.loads(m),'reason':r} for v,m,r in db.execute('SELECT version,members,reason FROM research_groups WHERE active=1 ORDER BY version')]
            if digest([g for g in live if all(uid in known for uid in g['members'])])!=manifest['groups_version']:raise ServiceError('다른 창에서 연구 묶음을 변경했습니다. 다시 확인해주세요.',409)
            if action=='group':
                members=body.get('members')
                if not isinstance(members,list) or any(not isinstance(uid,str) for uid in members) or not 2<=len(set(members))<=10 or any(uid not in known for uid in members):raise ServiceError('실제 출처 2~10개를 선택해주세요.',400)
                union=set(members)
                for g in groups:
                    if union.intersection(g['members']):union.update(g['members'])
                if len(union)>10:raise ServiceError('연구 묶음은 최대 10개 출처까지 지원합니다.',400)
                for g in groups:
                    if union.intersection(g['members']):db.execute('UPDATE research_groups SET active=0 WHERE version=?',(g['id'],))
                identity=str(uuid.uuid4());db.execute('INSERT INTO research_groups VALUES (?,1,?,?)',(identity,json.dumps(sorted(union)),reason.strip()))
            elif action=='ungroup':
                identity=body.get('group_id')
                if identity not in {g['id'] for g in groups}:raise ServiceError('현재 연구 묶음을 찾지 못했습니다.',400)
                db.execute('UPDATE research_groups SET active=0 WHERE version=?',(identity,))
            else:raise ServiceError('묶기/해제 작업을 확인해주세요.',400)
            db.execute('INSERT INTO group_events VALUES (?,?,?,?)',(str(uuid.uuid4()),time.time(),action,json.dumps({'group_id':identity,'reason':reason.strip()},ensure_ascii=False)))
        return self.manifest()
    def compare(self,target,ranked,known,groups):
        grouped={uid:g for g in groups for uid in g['members']};seen=set();out=[];q=normalize(target['originalText'])
        for _,record,match in ranked:
            group=grouped.get(record['uid']);identity=group['id'] if group else record['uid']
            if identity in seen:continue
            seen.add(identity);sources=[known[uid] for uid in group['members']] if group else [record]
            fragments=[q[b.a:b.a+b.size] for b in difflib.SequenceMatcher(None,q,normalize(record['title']),autojunk=False).get_matching_blocks() if b.size>=2][:6]
            exact=any(normalize(r['title'])==q for r in sources)
            out.append({'study_id':identity,'group_confirmed':bool(group),'sources':sources,'match':'제목 일치 (공백·기호 제외)' if exact else match,'exact_title':exact,'commonality':'제목에서 함께 나타나는 표현: '+(', '.join(fragments) if fragments else '글자 수준에서 확인되지 않음'),'difference':'입력과 기존 제목의 표현을 비교한 결과입니다. 제목만으로 연구 질문·변수·방법이 실제로 같은지는 확인할 수 없습니다.','needs_confirmation':'원문 보고서에서 연구 질문, 바꾸는 조건, 측정 지표와 절차를 확인해주세요.'})
            if len(out)==5:break
        return out
    @staticmethod
    def semantic_score(a,b):
        if not isinstance(a,list) or not isinstance(b,list) or not a or not b or any(type(n) not in (int,float) or not math.isfinite(n) for n in a+b):raise ServiceError('의미 검색 벡터 형식이 올바르지 않습니다.')
        return cosine(a,b)
    def check(self,body):
        topics=targets_from(body);method=body.get('method','lexical')
        parent=None
        if body.get('base_version'):
            try:parent=self.get(body['base_version'])['version']
            except ServiceError:pass
        if method not in ('lexical','semantic'):raise ServiceError('검사 방식을 확인해주세요.',400)
        manifest={'fingerprint':'unavailable','criteria_version':CRITERIA,'search_version':SEARCH_VERSION,'embedding_model':EMBED_MODEL};failure=None;known={};groups=[];vectors=None
        try:
            known,groups,manifest=self.snapshot()
            if method=='semantic':
                compatible=digest([(r['uid'],r['title']) for r in known.values()])==self.service.data_hash
                if not self.service.index or not compatible:raise ServiceError('완성된 의미 검색 색인이 없습니다. 제목 검사로 진행하거나 색인을 준비한 뒤 다시 시도해주세요.',503)
                vectors=self.service.factory().embed(['\n'.join([t['originalText']]+[t[k] for k in ('question','target','method','measurement') if t[k]]) for t in topics])
                if len(vectors)!=len(topics):raise ServiceError('의미 검색 응답 개수가 올바르지 않습니다.')
                if any(uid not in self.service.index for uid in known):raise ServiceError('의미 검색 색인과 자료가 일치하지 않습니다.')
        except (ServiceError,OSError,ValueError,KeyError,TypeError) as e:failure=str(e) if isinstance(e,ServiceError) else '검색 자료나 색인을 읽지 못했습니다. 자료를 확인한 뒤 재검사해주세요.'
        results=[]
        for i,target in enumerate(topics):
            q=normalize(target['originalText']);ranked=[];problem=failure
            peers=[]
            for other in topics:
                if other['id']==target['id']:continue
                score,common=lexical(q,normalize(other['originalText']))
                exact=q==normalize(other['originalText'])
                if exact or (common>=2 and score>=0.3):peers.append({'topic_id':other['id'],'title':other['originalText'],'origin':other['origin'],'exact_title':exact,'reason':'입력한 주제끼리 제목이 같음' if exact else '입력한 주제끼리 일부 제목 표현이 유사함'})
            if not problem:
                try:
                    for uid,row in known.items():
                        n=normalize(row['title']);score,common=lexical(q,n);exact=q==n;semantic=self.semantic_score(vectors[i],self.service.index[uid]) if vectors is not None else -1
                        if exact or (common>=2 and score>=0.15) or semantic>=0.45:
                            ranked.append((3 if exact else max(score,semantic),row,'의미 검색 후보' if semantic>=0.45 else '제목 일부 표현 일치'))
                    ranked.sort(key=lambda x:(-x[0],x[1]['uid']))
                except (ServiceError,KeyError,ValueError,TypeError) as e:problem=str(e) if isinstance(e,ServiceError) else '검색 색인을 비교하지 못했습니다.'
            matches=self.compare(target,ranked,known,groups) if not problem else []
            status=INCOMPLETE if problem else RISK if any(m['exact_title'] for m in matches) or any(p['exact_title'] for p in peers) else SIMILAR if matches or peers else NONE
            results.append({'topic_id':target['id'],'title':target['originalText'],'origin':target['origin'],'status':status,'reason':problem or ('제목 기준으로 같은 제목이 발견됐습니다. 동일 연구·표절로 확정한 것은 아닙니다.' if status==RISK else '관련 제목이 있어 원문과 차별점 검토가 필요합니다.' if status==SIMILAR else '이번 검색 방식과 현재 보유 제목 자료 범위에서 관련 후보를 찾지 못했습니다.'),'matches':matches,'peer_matches':peers[:5],'candidate_group_id':digest(q),'additional_checks':['기존 작품의 보고서 전문·연구 질문·변수·방법 확인','제공한 질문·대상·방법·측정 지표와 원문 대조'],'improvements':['제목만 바꾸지 말고 비교 조건·측정 지표·검증 질문의 실질적 차이를 구체화하세요.'],'review':None,'recommendation_hold':status in (RISK,INCOMPLETE),'limitations':LIMITATION})
        return self.save({'parent_version':parent,'topics':topics,'topics_fingerprint':digest(topics),'manifest':manifest,'method':method,'semantic_executed':vectors is not None and not failure,'scope':'현재 보유 작품 제목; 지도논문 제외; 보고서 본문 미확보','results':results,'criteria_version':CRITERIA})
    def review(self,body):
        if not isinstance(body,dict):raise ServiceError('검토 요청 형식을 확인해주세요.',400)
        previous=self.get(body.get('version'));self.require_current(previous)
        result=copy.deepcopy(previous);entry=next((r for r in result['results'] if r['topic_id']==body.get('topic_id')),None)
        decision,reason=body.get('decision'),body.get('reason')
        if entry is None or decision not in ('approved','hold') or not isinstance(reason,str) or not 1<=len(reason.strip())<=1000:raise ServiceError('검토 대상·승인/보류·근거를 확인해주세요.',400)
        if entry['status']==INCOMPLETE and decision=='approved':raise ServiceError('미완료 검사는 승인할 수 없습니다. 먼저 재검사해주세요.',400)
        entry['review']={'decision':decision,'reason':reason.strip(),'actor':'teacher','created_at':time.time()};entry['recommendation_hold']=decision!='approved'
        result['parent_version']=previous['version'];return self.save(result)
    def evaluation_context(self,version,ideas,topics=None,selected_ids=None):
        result=self.get(version);self.require_current(result)
        if topics is not None and digest(topics)!=result['topics_fingerprint']:raise ServiceError('주제 보완 정보가 변경됐습니다. 다시 검사해주세요.',409)
        if selected_ids is not None:
            known={t['id']:i for i,t in enumerate(result['topics'])}
            if len(selected_ids)!=len(ideas) or len(set(selected_ids))!=len(selected_ids) or any(uid not in known for uid in selected_ids):raise ServiceError('평가할 주제와 검사 결과를 확인해주세요.',400)
            order=[known[uid] for uid in selected_ids]
            result=dict(result,topics=[result['topics'][i] for i in order],results=[result['results'][i] for i in order])
        if [t['originalText'].strip() for t in result['topics']]!=ideas:raise ServiceError('주제·질문 또는 방법이 변경됐습니다. 다시 검사해주세요.',409)
        return result
