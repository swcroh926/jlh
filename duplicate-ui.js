import {duplicateTopics,duplicateSourceKey} from './duplicate.mjs';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function link(url){try{const u=new URL(url);return u.protocol==='https:'&&['www.science.go.kr','ssei.sen.go.kr','www.gise.kr','gice.gen.go.kr','aicei.ice.go.kr','gnse.gne.go.kr','www.gbe.kr','org.jje.go.kr'].includes(u.hostname)?u.href:null}catch{return null}}
export function mountDuplicates(root,project,actions){
 let topics=duplicateTopics(project),sourceKey=duplicateSourceKey(project),manifest=null,busy=false;
 const previous=project.duplicateCheck;let active=previous?.sourceKey===sourceKey?previous.result:null;
 const reviewDraft={},selectedSources=new Set();
 root.innerHTML=`<article class="duplicate-panel"><div class="eyebrow">CHECK_DUPLICATE</div><h2>기존 작품과 중복 위험 확인</h2><p>제목이 비슷한 작품을 찾고 차별점을 검토합니다. 제목만으로 같은 연구·표절이라고 확정하지 않습니다. 지도논문은 제외하며, 별도 제목 검색에서 참고할 수 있습니다.</p><div class="row"><button type="button" class="primary duplicate-lexical">제목 기준 검사 (무료)</button><button type="button" class="text duplicate-semantic" disabled>의미 검색 포함 검사 (API 사용)</button></div><p class="duplicate-status" role="status">자료와 이전 검사 버전을 확인하고 있습니다…</p><p class="duplicate-coverage"></p><details><summary>탐구 질문·방법 등 보완 정보 (선택)</summary><div class="duplicate-details">${topics.map(t=>`<fieldset><legend>${esc(t.originalText)}</legend>${[['question','탐구 질문'],['target','탐구 대상'],['method','바꾸는 조건·접근 방법'],['measurement','측정 지표']].map(([k,label])=>`<label>${label}<input data-topic="${esc(t.id)}" data-detail="${k}" maxlength="1000" value="${esc(t[k])}"></label>`).join('')}</fieldset>`).join('')}</div><small>입력한 정보는 보존하지만 기존 자료에는 제목만 있어 방법의 일치 여부까지 비교할 수 없습니다. 수정하면 다시 검사해야 합니다.</small></details><div class="duplicate-results" aria-live="polite"></div><details class="research-grouping"><summary>같은 연구임을 확인한 출처 묶기</summary><p>제목이 같다는 이유만으로 묶지 않습니다. 원문에서 같은 연구임을 확인한 경우에만 아래 출처를 선택하고 근거를 기록하세요.</p><div class="duplicate-group-choices"></div><label>확인 근거 또는 해제 이유<textarea class="duplicate-group-reason" maxlength="1000" rows="2"></textarea></label><button type="button" class="text duplicate-group">선택한 출처를 같은 연구로 묶기</button><div class="duplicate-groups"></div></details></article>`;
 const status=root.querySelector('.duplicate-status'),results=root.querySelector('.duplicate-results');
 function stale(){return !active||!manifest||active.manifest.fingerprint!==manifest.manifest.fingerprint||previous?.sourceKey!==sourceKey||project.staleResults?.duplicate}
 function draw(){
  if(!active){results.innerHTML='<p>검사 전입니다. 원본 주제를 확정한 뒤 위 검사 버튼을 눌러주세요.</p>';return}
  results.innerHTML=`${stale()?'<div class="notice">재검사 필요: 아래는 이전 검사 기록입니다. 새 조건·자료의 결과로 사용하지 않습니다.</div>':''}<p>검사 범위: ${esc(active.scope)} · ${active.method==='semantic'?'제목+의미 검색':'제목 표현 검색만 (의미 검색 미실행)'}</p>${active.results.map(r=>`<section class="duplicate-result"><h3>${esc(r.title)}</h3><span class="tag risk-${r.status==='중복 위험'?'high':r.status==='검사 미완료'?'error':'normal'}">${esc(r.status)}</span>${r.review?`<span class="tag">교사 ${r.review.decision==='approved'?'승인':'보류'} · ${r.recommendation_hold?'자동 추천 보류':'검토 보류 해제'}</span>`:r.recommendation_hold?'<span class="tag">자동 추천 보류</span>':''}<p>${esc(r.reason)}</p><details><summary>유사 연구·차이·보완 방향 펼치기 (${r.matches.length}건)</summary>${r.matches.map(m=>`<div class="award-result"><strong>${esc(m.match)}${m.group_confirmed?' · 같은 연구로 확인된 출처 묶음':''}</strong>${m.sources.map(s=>{const url=link(s.url);return `<p>${esc(s.source)} · ${esc(s.year)} · ${esc(s.title)}${url?` <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">원문 ↗</a>`:''}</p>`}).join('')}<p>${esc(m.commonality)}</p><p>${esc(m.difference)}</p><p>${esc(m.needs_confirmation)}</p></div>`).join('')||'<p>이 검사 범위에서 제시할 수 있는 작품이 없습니다.</p>'}${r.peer_matches.length?`<h4>학생의 원본·생성 주제 사이 유사성</h4>${r.peer_matches.map(p=>`<p>${esc(p.origin==='generated'?'생성':'원본')} · ${esc(p.title)} · ${esc(p.reason)}</p>`).join('')}`:''}<p>추가 확인: ${r.additional_checks.map(esc).join(' / ')}</p><p>보완 방향: ${r.improvements.map(esc).join(' / ')}</p><small>${esc(r.limitations)}</small></details><label>차별성 검토 근거<textarea class="duplicate-review-reason" data-review-topic="${esc(r.topic_id)}" rows="2" maxlength="1000">${esc(reviewDraft[r.topic_id]??r.review?.reason??'')}</textarea></label><button type="button" class="text duplicate-review" data-topic="${esc(r.topic_id)}" data-decision="approved" ${stale()||r.status==='검사 미완료'?'disabled':''}>차별성 확인 후 승인</button><button type="button" class="text duplicate-review" data-topic="${esc(r.topic_id)}" data-decision="hold" ${stale()?'disabled':''}>검토 보류</button></section>`).join('')}<small>검사 기준 ${esc(active.criteria_version)} · 버전 ${esc(active.version)}</small>`;
  const unique=new Map();for(const r of active.results)for(const m of r.matches)for(const s of m.sources)unique.set(s.uid,s);
  root.querySelector('.duplicate-group-choices').innerHTML=[...unique.values()].map(s=>`<label><input type="checkbox" class="duplicate-group-member" value="${esc(s.uid)}" ${selectedSources.has(s.uid)?'checked':''}>${esc(s.source)} · ${esc(s.title)}</label>`).join('');
  root.querySelectorAll('.duplicate-review-reason').forEach(el=>el.oninput=()=>reviewDraft[el.dataset.reviewTopic]=el.value);
  root.querySelectorAll('.duplicate-group-member').forEach(el=>el.onchange=()=>{if(el.checked)selectedSources.add(el.value);else selectedSources.delete(el.value)});
  root.querySelectorAll('.duplicate-review').forEach(b=>b.onclick=()=>{const reason=[...root.querySelectorAll('[data-review-topic]')].find(x=>x.dataset.reviewTopic===b.dataset.topic).value;send('/api/duplicates/review',{version:active.version,topic_id:b.dataset.topic,decision:b.dataset.decision,reason})});
 }
 async function refresh(){
  try{
   const response=await fetch('/api/duplicates/manifest');const body=await response.json();if(!response.ok)throw Error(body.error||'자료를 확인하지 못했습니다.');if(!root.isConnected)return;
   manifest=body;actions.onManifest(body.manifest);
   root.querySelector('.duplicate-coverage').textContent=`보유 제목 ${body.manifest.record_count.toLocaleString()}건 · 지도논문 제외. 전국 전체 자료 수집·보고서 전문 검색을 완료했다는 뜻은 아닙니다.`;
   root.querySelector('.duplicate-semantic').disabled=busy||(!body.semantic_available||!body.api_configured);
   status.textContent=active?(stale()?'자료·주제·기준이 변경되어 재검사가 필요합니다.':'저장된 검사 결과를 확인했습니다.'):'무료 제목 검사를 먼저 사용할 수 있습니다. 의미 검사는 색인·API 연결이 필요합니다.';
   root.querySelector('.duplicate-groups').innerHTML=body.groups.map(g=>`<p>${g.members.map(esc).join(' / ')} · ${esc(g.reason)} <button class="text duplicate-ungroup" type="button" data-group="${esc(g.id)}">묶음 해제</button></p>`).join('');
   root.querySelectorAll('.duplicate-ungroup').forEach(b=>b.onclick=()=>send('/api/duplicates/group',{action:'ungroup',group_id:b.dataset.group,fingerprint:manifest.manifest.fingerprint,reason:root.querySelector('.duplicate-group-reason').value}));draw();
  }catch(e){if(root.isConnected){manifest=null;project={...project,staleResults:{...project.staleResults,duplicate:true}};actions.onManifest(null);status.textContent='검사 미완료: '+(e.message||'로컬 서버를 확인해주세요.');draw()}}
 }
 function disabled(value){busy=value;root.querySelectorAll('button,input,textarea').forEach(b=>b.disabled=value);if(!value){root.querySelector('.duplicate-semantic').disabled=(!manifest?.semantic_available||!manifest?.api_configured);draw()}}
 async function send(path,body){
  let failureStatus=0;
  disabled(true);status.textContent='검사·검토 내용을 처리하고 있습니다…';
  try{
   const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();failureStatus=response.status;if(!response.ok)throw Error(result.error||'검사를 처리하지 못했습니다.');if(!root.isConnected)return;
   if(path.endsWith('/group')){actions.onManifest(null);await refresh();status.textContent='연구 묶음을 변경했습니다. 이전 검토 승인도 새 검사에 자동 적용되지 않습니다. 다시 검사해주세요.'}
   else actions.onResult(result,sourceKey);
  }catch(e){if(root.isConnected){const invalid=path.endsWith('/check')||failureStatus===409;if(invalid){manifest=null;project={...project,staleResults:{...project.staleResults,duplicate:true}};actions.onManifest(null)}status.textContent=(invalid?'검사 미완료: ':'검토 저장 실패: ')+(e.message||'연결 오류입니다. 기존 기록은 보존합니다.')}}
  finally{if(root.isConnected)disabled(false)}
 }
 root.querySelectorAll('[data-detail]').forEach(input=>input.oninput=()=>{
  const details={...project.duplicateDetails};for(const el of root.querySelectorAll('[data-detail]'))details[el.dataset.topic]={...details[el.dataset.topic],[el.dataset.detail]:el.value};
  project={...project,duplicateDetails:details};topics=duplicateTopics(project);sourceKey=duplicateSourceKey(project);actions.onEdit(details);draw();status.textContent='질문·방법을 수정했습니다. 이전 결과를 보존하고 재검사가 필요합니다.';
 });
 root.querySelector('.duplicate-lexical').onclick=()=>send('/api/duplicates/check',{topics,method:'lexical',base_version:active?.version});
 root.querySelector('.duplicate-semantic').onclick=()=>{if(confirm('의미 검색은 AI 임베딩 API를 사용할 수 있습니다. 비용이 발생할 수 있으며 검사 실패 시 미완료로 남습니다. 진행할까요?'))send('/api/duplicates/check',{topics,method:'semantic',base_version:active?.version})};
 root.querySelector('.duplicate-group').onclick=()=>send('/api/duplicates/group',{action:'group',fingerprint:manifest?.manifest.fingerprint,members:[...root.querySelectorAll('.duplicate-group-member:checked')].map(c=>c.value),reason:root.querySelector('.duplicate-group-reason').value});
 draw();refresh();
}
