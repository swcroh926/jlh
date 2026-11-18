import {currentDuplicate} from './duplicate.mjs';
import {confirmedInterest} from './interest.mjs';
import {evaluationKey,evaluationPayload,splitTopics} from './project.mjs';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const axes={originality:'차별성',award_fit:'탐구 기준 적합도',feasibility:'현실화 가능성',interest:'관심사 관련성'};
export function mountEvaluation(root,project,onSave,onSelect){
 const projectKey=evaluationKey(project);
 const ideas=splitTopics(project.ideas);
 const profile=confirmedInterest(project),check=currentDuplicate(project);
 const checked=check&&check.results.every(r=>r.status!=='검사 미완료');
 root.innerHTML=`<article><div class="eyebrow">TOOL_EVAL</div><h2>아이디어 AI 평가</h2><p>전체 아이디어를 네 기준으로 평가합니다. 제목 자료에 근거한 보조 의견이며 수상 확률이나 표절 판정이 아닙니다. 이름·지역은 AI에 전달하지 않습니다. 현재는 기존 4항목 평가이며, 명세의 5항목 가중 평가는 다음 작업에서 연결합니다.</p><div class="fields"><label>사용 가능한 장비·공간<textarea class="eval-equipment" maxlength="1000" rows="2" placeholder="예: 교실, 전자저울, 현미경 없음"></textarea></label><label>추가 관심 선호 (선택)<textarea class="eval-interests" maxlength="1000" rows="2" placeholder="확정한 원본 기반 관심사가 우선 사용됩니다."></textarea></label></div><label>PASS 기준 점수 (이 값을 초과해야 통과)<input class="eval-threshold" type="number" min="0" max="100" value="70"></label><div class="eval-access" hidden><label>선생님용 접근 코드<input type="password" class="eval-code" autocomplete="off" maxlength="256"></label><button type="button" class="primary eval-login">AI 평가 연결</button><button type="button" class="text eval-logout" hidden>연결 해제</button><small>접근 코드는 선생님에게 전달받으세요. OpenAI API 키를 입력하는 곳이 아닙니다.</small></div><p class="eval-status" role="status">AI 평가 연결을 확인하고 있습니다…</p><button type="button" class="primary eval-run" disabled>전체 ${ideas.length}개 아이디어 평가</button><div class="eval-results" aria-live="polite"></div></article>`;
 const status=root.querySelector('.eval-status'),button=root.querySelector('.eval-run'),resultRoot=root.querySelector('.eval-results');
 function show(result,selectable=true){
  const ready=selectable&&result.next_step==='select';
  resultRoot.innerHTML=`<div class="banner"><strong>추천 가능 ${result.passed_count}개 / 전체 ${result.evaluations.length}개</strong><span>점수 기준 ${result.threshold}점 초과 · ${result.search_mode==='semantic'?'의미 검색':'제목 표현 검색'} · ${esc(result.model)}</span></div><p>${ready?'통과한 후보 중 평균 점수 상위 3개를 선택할 수 있습니다.':'통과 후보가 3개 미만입니다. 아이디어를 보완해 다시 평가해주세요. 자동 아이디어 생성은 아직 연결 전입니다.'}</p>${result.evaluations.map(e=>`<div class="award-result"><h3>${esc(e.title)} · ${e.average}점 · ${e.passed?'점수 통과':'보완 필요'}</h3>${e.duplicate_status?`<p><strong>${esc(e.duplicate_status)}</strong> · ${e.recommendation_hold?'자동 추천 보류':'검토 조건 충족'}</p>`:''}${Object.entries(axes).map(([key,label])=>`<p><strong>${label} ${e[key].score}점</strong><br>${esc(e[key].reason)}</p>`).join('')}<p><strong>확인할 조건</strong><br>${e.uncertainties.map(esc).join('<br>')||'추가 기재 없음'}</p><p><strong>개선 제안</strong><br>${e.improvements.map(esc).join('<br>')||'추가 기재 없음'}</p><p><strong>평가에 참고한 제목</strong></p>${e.sources.map(s=>{let url;try{const u=new URL(s.url);if(u.protocol==='https:'&&['www.science.go.kr','ssei.sen.go.kr'].includes(u.hostname))url=u.href}catch{}return `<p>${esc(s.source)} · ${esc(s.year)} · ${esc(s.title)}${url?` <a href="${esc(url)}" target="_blank" rel="noopener noreferrer">원문 ↗</a>`:''}</p>`}).join('')||'<p>인용된 제목 없음 · 독창성을 입증하는 것은 아닙니다.</p>'}${ready&&!e.recommendation_hold&&result.top_three_indices.includes(e.idea_index)?`<button type="button" class="primary eval-select" data-index="${e.idea_index}">이 후보 선택</button>`:''}</div>`).join('')}<small>평가 기준 ${esc(result.rubric_version)} · 선택 후 실험 계획은 현재 공통 템플릿입니다.</small>`;
  resultRoot.querySelectorAll('.eval-select').forEach(b=>b.onclick=()=>onSelect(result.evaluations.find(e=>e.idea_index===Number(b.dataset.index))));
 }
 root.querySelector('.eval-equipment').value=project.equipment||'';
 const prior=project.aiEvaluation;
 if(prior?.projectKey===projectKey){
  root.querySelector('.eval-equipment').value=prior.conditions.equipment;
  root.querySelector('.eval-interests').value=prior.conditions.interests;
  root.querySelector('.eval-threshold').value=prior.conditions.threshold;
  show(prior.result);
 }else if(prior){
  show(prior.result,false);
  resultRoot.insertAdjacentHTML('afterbegin','<div class="notice" role="status">재평가 필요: 조건·관심사·중복 검사 또는 원본 주제가 변경됐습니다. 아래는 이전 결과이며 새 조건의 결과로 사용할 수 없습니다.</div>');
 }
 for(const el of root.querySelectorAll('.eval-equipment,.eval-interests,.eval-threshold'))el.addEventListener('input',()=>{resultRoot.textContent='조건이 변경됐습니다. 다시 평가하면 결과가 갱신됩니다.'});
 const access=root.querySelector('.eval-access'),login=root.querySelector('.eval-login'),logout=root.querySelector('.eval-logout'),code=root.querySelector('.eval-code');
 async function refresh(){
  try{
   const r=await fetch('/api/health');if(!r.ok)throw Error();const h=await r.json();if(!root.isConnected)return;
   access.hidden=!h.auth_required;login.hidden=!!h.authenticated;code.parentElement.hidden=!!h.authenticated;logout.hidden=!h.authenticated;
   button.disabled=!profile||!checked||!h.configured||(h.auth_required&&!h.authenticated);
   status.textContent=!profile?'위 관심사 분류를 먼저 확인하고 확정해주세요.':!checked?'위 중복 위험 검사를 완료해주세요. 이전 검사·검토 결과는 보존됩니다.':!h.configured?'AI 평가 준비 중입니다. 연결이 완료되면 이곳에서 평가할 수 있습니다.':h.auth_required&&!h.authenticated?'접근 코드를 입력하면 AI 평가를 사용할 수 있습니다.':'평가할 때 아이디어·학년·예산·기간과 아래 조건을 OpenAI에 전달합니다.';
  }catch{if(root.isConnected){button.disabled=true;status.textContent='AI 평가 준비 중입니다. 현재 사이트에서는 제목 검색을 먼저 이용해주세요.'}}
 }
 async function connect(path,body){
  login.disabled=true;
  try{
   const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await r.json();code.value='';if(!r.ok)throw Error(data.error||'연결하지 못했습니다.');await refresh();
  }catch(e){status.textContent=e.message}finally{login.disabled=false}
 }
 login.onclick=()=>connect('/api/login',{code:code.value});
 code.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();login.click()}});
 logout.onclick=()=>connect('/api/logout',{});
 refresh();
 button.onclick=async()=>{
  const equipment=root.querySelector('.eval-equipment').value,interests=root.querySelector('.eval-interests').value,threshold=Number(root.querySelector('.eval-threshold').value);
  if(!Number.isFinite(threshold)||threshold<0||threshold>100){status.textContent='기준 점수는 0~100 사이로 입력해주세요.';return}
  button.disabled=true;status.textContent='관련 작품을 찾고 아이디어를 평가하고 있습니다…';
  try{
   const response=await fetch('/api/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(evaluationPayload(project,{equipment,interests,threshold}))});
   const body=await response.json();if(response.status===401)await refresh();if(!response.ok)throw Error(body.error||'평가를 완료하지 못했습니다.');
   onSave({projectKey,inputIdeas:project.ideas,conditions:{equipment,interests,threshold},result:body});if(!root.isConnected)return;show(body);status.textContent=body.cached?'동일 조건의 저장된 평가 결과를 불러왔습니다.':'평가 결과를 저장했습니다.';
  }catch(e){if(root.isConnected)status.textContent=e.message||'평가에 실패했습니다. 잠시 후 다시 시도해주세요.'}
  finally{if(root.isConnected){const message=status.textContent;await refresh();status.textContent=message}}
 };
}
