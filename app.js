import {mountGeneration} from './generation-ui.js';
import {duplicateSourceKey} from './duplicate.mjs';
import {mountDuplicates} from './duplicate-ui.js';
import {applyDuplicate,editDuplicate,setDuplicateManifest,currentDuplicate} from './duplicate.mjs';
import {mountInterests} from './interest-ui.js';
import {applyInterest,editInterest} from './interest.mjs';
import {mountInput} from './input-ui.js';
import {DEFAULT_SETTINGS,createProject,migrateProject,conditions,settingsProblems,applyDraft,confirmTopics,topicProblems,profileProblems,evaluationKey} from './project.mjs';
import {mountEvaluation} from './eval-ui.js';
import {mountSearch} from './search-ui.js';
import {evaluate,parseIdeas,experiments} from './model.mjs';
const key='jlh-project-v1',settingsKey='jlh-teacher-defaults-v1';
let defaults={...DEFAULT_SETTINGS};try{const saved=JSON.parse(localStorage.getItem(settingsKey));if(saved&&!settingsProblems(saved).length)defaults={...DEFAULT_SETTINGS,...saved};}catch{}
let state=createProject(defaults);try{const saved=JSON.parse(localStorage.getItem(key));if(saved&&[1,2].includes(saved.version))state=migrateProject(saved.project);}catch{}
state.generationPending=false;state.duplicateManifest=null; // Revalidate server data/criteria after every page load.
const app=document.querySelector('#app');const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const awardSearch = document.querySelector('#award-search');
const searchButton = document.querySelector('#open-award-search');
const stepButtons = [...document.querySelectorAll('#nav [data-step]')];

function canCompare() {
  return state.confirmedIdeas === state.ideas
    && !profileProblems(state).length
    && !topicProblems(state.ideas).length;
}

function markCurrent(button, current) {
  button.classList.toggle('active', current);
  if (current) button.setAttribute('aria-current', 'page');
  else button.removeAttribute('aria-current');
}

function renderNavigation() {
  const canContinue = canCompare();
  for (const button of stepButtons) {
    const step = Number(button.dataset.step);
    button.disabled = step > 0 && (!canContinue || (step > 1 && !state.selected));
    markCurrent(button, awardSearch.hidden && state.step === step);
  }
  markCurrent(searchButton, !awardSearch.hidden);
}

function openSearch() {
  if (!awardSearch.hidden) return;
  const panel = document.createElement('div');
  awardSearch.replaceChildren(panel);
  app.hidden = true;
  awardSearch.hidden = false;
  mountSearch(panel, parseIdeas(state.ideas));
  renderNavigation();
  panel.querySelector('h1').focus();
  window.scrollTo(0, 0);
}
function save(){try{localStorage.setItem(key,JSON.stringify({version:2,project:state}));document.querySelector('#save-status').textContent='이 브라우저에 저장됨'}catch{document.querySelector('#save-status').textContent='저장 실패 · 브라우저 저장 공간을 확인하세요'}}
function go(step) {
  if (step > 0 && !canCompare()) step = 0;
  const returningFromSearch = !awardSearch.hidden;
  if (returningFromSearch) {
    awardSearch.hidden = true;
    awardSearch.replaceChildren();
    app.hidden = false;
  }
  if (returningFromSearch && state.step === step) {
    renderNavigation();
  } else {
    state.step = step;
    save();
    render();
  }
  window.scrollTo(0, 0);
}
function archiveProjects(){const projects=[];try{for(let i=0;i<localStorage.length;i++){const key=localStorage.key(i);if(key.startsWith('jlh-project-archive:')){try{const value=JSON.parse(localStorage.getItem(key));if(value?.project)projects.push(value.project)}catch{}}}}catch{}return projects.filter(p=>p.id!==state.id);}
function activateProject(next){try{localStorage.setItem('jlh-project-archive:'+state.id,JSON.stringify({version:2,project:state}));localStorage.setItem(key,JSON.stringify({version:2,project:next}));state=next;render();window.scrollTo(0,0)}catch{document.querySelector('#settings-status').textContent='프로젝트'+'를 보관하지 못해 변경하지 않았습니다.'}}
function renderGeneration(){const interestProjectId=state.id;let generation=document.querySelector('#generation-panel');if(!generation){generation=document.createElement('section');generation.id='generation-panel';app.append(generation)}mountGeneration(generation,{...state},{
 onAuto:value=>{state.generationAutoEnabled=value;save()},
 onStart:id=>{state.generationAutoAttempt=id;state.generationPending=true;state.generationError='';save()},
 onError:message=>{if(state.id===interestProjectId){state.generationError=message;save()}},
 onFinish:()=>{if(state.id!==interestProjectId)return;state.generationPending=false;save();if(state.step===1)renderGeneration()},
 onResult:(result,sourceKey)=>{if(state.id!==interestProjectId)return;state.resultHistory.push({kind:'generation',value:result});if(sourceKey!==evaluationKey(state)){save();return}state.generation=result;
 if(result.topics?.length){state.generatedTopics=result.topics;state=editDuplicate(state,state.duplicateDetails||{});if(result.duplicate_check)state=applyDuplicate(state,result.duplicate_check,duplicateSourceKey(state));if(result.evaluation){if(state.aiEvaluation)state.resultHistory.push({kind:'evaluation',value:state.aiEvaluation});state.aiEvaluation={projectKey:evaluationKey(state),conditions:{...state.aiEvaluation.conditions,threshold:80},result:result.evaluation};state.staleResults.evaluation=false}}
 save();render()}
 });}
function renderEvaluation(){const evaluationProjectId=state.id;let evaluation=document.querySelector('#evaluation-panel');if(!evaluation){evaluation=document.createElement('section');evaluation.id='evaluation-panel';app.append(evaluation)}mountEvaluation(evaluation,{...state},value=>{if(state.id!==evaluationProjectId)return;if(state.aiEvaluation)state.resultHistory.push({kind:'evaluation',value:state.aiEvaluation,savedAt:new Date().toISOString()});state.aiEvaluation=value;state.staleResults.evaluation=value.projectKey!==evaluationKey(state);save();render()},e=>{const previous=state.selected;if(previous&&previous.title!==e.title&&!confirm('주제를 변경하면 실험 기록이 초기화됩니다. 계속할까요?'))return;if(previous?.title!==e.title){state.resultHistory.push({kind:'plan',selected:state.selected,notes:state.notes,research:state.research,savedAt:new Date().toISOString()});state.notes={};state.research=''}state.selected={id:e.idea_index,title:e.title,scores:[e.originality.score,e.inquiry.score,e.feasibility.score,e.utility.score,e.interest.score],average:e.average};go(2)});}
function heading(k,title,sub){return `<div class="eyebrow">${k}</div><h1>${title}</h1><p class="subtitle">${sub}</p>`}
function render(){renderNavigation();
if(state.step===0){mountInput(app,state,defaults,{
 onDraft:patch=>{state=applyDraft(state,patch);save();renderNavigation()},
 onDefaults:value=>{try{localStorage.setItem(settingsKey,JSON.stringify(value));defaults=value;return true}catch{return false}},
 onConfirm:()=>{state=confirmTopics(state);save();go(1)},
 listArchive:archiveProjects,onRestore:p=>activateProject(migrateProject(p)),onNew:()=>activateProject(createProject(defaults))
});}else if(state.step===1){const candidates=evaluate(parseIdeas(state.ideas));app.innerHTML=heading('STEP 02 · CHOOSE','나의 탐구 후보를 만나보세요','평균 점수 순으로 최대 3개를 보여줍니다. 현재 점수는 기능 확인용 예시입니다.')+`<div class="banner">아이디어를 더 탐색하고 싶나요? <button id="back" class="text">아이디어 수정하기 ←</button></div><div class="cards">${candidates.map((c,i)=>`<article><span class="tag">후보 ${i+1} · 예시 평가</span><h2>${esc(c.title)}</h2>${currentDuplicate(state)?.results[c.id]?`<p><strong>${esc(currentDuplicate(state).results[c.id].status)}</strong> · ${currentDuplicate(state).results[c.id].recommendation_hold?'실제 자동 추천 보류':'검사 상태 참고'}</p>`:''}<div class="score">${c.average}<small> / 100</small></div>${['차별성','대회 기준 적합도','현실화 가능성','관심사 관련성'].map((x,j)=>`<div class="metric"><span>${x}</span><b>${c.scores[j]}</b></div><progress max="100" value="${c.scores[j]}"></progress>`).join('')}<p class="muted">‘비슷한 작품 찾아보기’ 메뉴에서 수집 자료의 제목을 검색할 수 있습니다. 이 평가 점수는 여전히 예시입니다. 이 점수로 주제의 우열을 판단하지 마세요.</p><h3>예상 실험 흐름</h3><p>예비 측정 → 조건별 비교 → 결과 재확인</p><small>소요 시간·비용: 주제별 산정 전</small><button class="primary select" data-id="${c.id}">이 주제로 계획하기 →</button></article>`).join('')}</div>`;
}else if(state.step===2){app.innerHTML=heading('STEP 03 · PLAN','궁금증을 실험으로 바꿔볼까요?','아래는 공통 설계 템플릿입니다. 주제에 맞게 선생님과 검토한 뒤 진행하세요.')+`<div class="banner"><strong>${esc(state.selected?.title)}</strong><span>예산 ${conditions(state).budget.toLocaleString()}원 · 목표 ${esc(state.weeks)}주 · 주 1회 ${esc(state.hoursPerSession)}시간 · ${esc(state.location)}</span></div><article><h2>선행 연구</h2><p>실제 검색 서비스 연결 전입니다. 확인한 자료의 제목·출처·요약을 직접 보관할 수 있습니다.</p><label>자료 및 요약<textarea id="research" rows="3" placeholder="자료 제목 / 원문 URL / 알게 된 점">${esc(state.research||'')}</textarea></label></article><div class="cards">${experiments.map((e,i)=>`<article><span class="tag">실험 0${i+1}</span><h2>${e.title}</h2><p>${e.goal}</p><ul>${e.steps.map(s=>`<li>${s}</li>`).join('')}</ul><small>준비물·구매처·비용: 확인 필요<br>관찰·대기 시간: 주제별 확인 필요</small></article>`).join('')}</div><button id="record" class="primary">실험 기록 시작하기 →</button>`;
}else{app.innerHTML=heading('STEP 04 · RECORD','발견의 순간을 기록해요','예상과 다른 결과도 소중한 발견입니다. 기록은 선택이며 이 브라우저에 저장됩니다.')+`<div class="banner"><strong>${esc(state.selected?.title)}</strong></div>${experiments.map((e,i)=>`<article><h2>${e.title}</h2><div class="fields"><label>실험 과정과 관찰<textarea data-note="${i}" data-field="process" rows="4" placeholder="어떤 조건에서 어떻게 진행했나요?">${esc(state.notes?.[i]?.process||'')}</textarea></label><label>측정 결과와 해석<textarea data-note="${i}" data-field="result" rows="4" placeholder="측정값, 단위, 반복 횟수를 함께 적어주세요.">${esc(state.notes?.[i]?.result||'')}</textarea></label></div><p class="muted">피드백 체크: 비교 조건이 같았나요? 반복 측정했나요? 가설과 다른 결과도 기록했나요?</p></article>`).join('')}<button id="export" class="primary">프로젝트 기록 내려받기 (JSON)</button><p class="muted">AI 결과 분석과 보고서 파일 생성은 추후 연결됩니다.</p>`}if(state.step>0){if(state.staleResults?.plan&&(state.step===2||state.step===3))app.insertAdjacentHTML('afterbegin','<div class="notice" role="status">조건 또는 주제가 변경됐습니다. 이전 실험 계획·기록을 보존하고 있으며 재검토가 필요합니다.</div>');}bind();if(state.step===1){const interestProjectId=state.id;const interest=document.createElement('section');interest.id='interest-panel';app.insertBefore(interest,app.querySelector('.cards'));mountInterests(interest,{...state},{
 onEdit:draft=>{if(state.id!==interestProjectId)return;state=editInterest(state,draft);save();renderEvaluation()},
 onResult:(result,key)=>{if(state.id!==interestProjectId)return;state=applyInterest(state,result,key);save();render()}
});const duplicate=document.createElement('section');duplicate.id='duplicate-panel';interest.after(duplicate);mountDuplicates(duplicate,{...state},{
 onEdit:details=>{if(state.id!==interestProjectId)return;state=editDuplicate(state,details);save();renderEvaluation()},
 onManifest:manifest=>{if(state.id!==interestProjectId)return;state=setDuplicateManifest(state,manifest);save();renderEvaluation();renderGeneration()},
 onResult:(result,key)=>{if(state.id!==interestProjectId)return;state=applyDuplicate(state,result,key);save();render()}
});renderEvaluation();renderGeneration();}}
function bind(){document.querySelector('#back')?.addEventListener('click',()=>go(0));document.querySelector('#record')?.addEventListener('click',()=>go(3));document.querySelectorAll('.select').forEach(b=>b.onclick=()=>{const selected=evaluate(parseIdeas(state.ideas)).find(c=>c.id===+b.dataset.id);if(state.selected&&state.selected.title!==selected.title&&!confirm('주제를 변경하면 이전 실험 기록과 선행 연구가 초기화됩니다. 계속할까요?'))return;if(state.selected?.title!==selected.title){state.resultHistory.push({kind:'plan',selected:state.selected,notes:state.notes,research:state.research,savedAt:new Date().toISOString()});state.notes={};state.research=''}state.selected=selected;go(2)});document.querySelector('#research')?.addEventListener('input',e=>{state.research=e.target.value;save()});document.querySelectorAll('[data-note]').forEach(el=>el.oninput=()=>{state.notes[el.dataset.note]??={};state.notes[el.dataset.note][el.dataset.field]=el.value;save()});document.querySelector('#export')?.addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({version:2,project:state},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='science-project.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)})}
for (const button of stepButtons) {
  button.addEventListener('click', () => go(Number(button.dataset.step)));
}
searchButton.addEventListener('click', openSearch);
document.querySelector('.brand').addEventListener('click', event => {
  if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  go(0);
});
state.step = 0;
render();
