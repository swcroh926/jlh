import {sampleIdeas} from './model.mjs';
import {MAX_ORIGINAL_TOPICS,conditions,topicProblems,profileProblems,splitTopics,settingsProblems} from './project.mjs';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function mountInput(root,project,defaults,actions){
 root.innerHTML=`<div class="page-heading row"><h1>주제 입력</h1><button type="button" id="new-project" class="text">새 프로젝트</button></div>
 <form id="ideas-form">
 <article class="topic-card">
  <div class="row topic-header"><h2><label for="ideas">원본 주제 목록</label></h2><button type="button" class="text" id="sample">예시 넣기</button></div>
  <p id="topic-hint">한 줄에 하나씩, 최대 ${MAX_ORIGINAL_TOPICS}개를 적어주세요.</p>
  <textarea id="ideas" name="ideas" rows="5" maxlength="100000" aria-describedby="topic-hint topic-count" placeholder="학생이 작성한 주제를 입력하세요.">${esc(project.ideas)}</textarea>
  <div class="row topic-tools">
   <label class="upload">문서에서 주제 가져오기<input id="file" type="file" accept=".txt,.docx,.hwpx,.hwp" aria-describedby="file-hint"></label>
   <p id="topic-count"></p>
  </div>
  <small id="file-hint">TXT·DOCX·HWPX 지원 · HWP는 변환 도구가 있을 때 시도합니다. 스캔 문서 OCR은 제외합니다.</small>
 <section id="file-preview" hidden><h3>추출 결과 확인</h3><p id="file-status" role="status"></p><textarea id="extracted-text" rows="6" maxlength="100000" aria-label="추출된 주제 수정"></textarea><p>한 주제를 한 줄로 정리하세요. 아래 버튼을 누르기 전에는 기존 목록을 변경하지 않습니다.</p><button type="button" id="append-file" class="primary">기존 목록에 추가</button><button type="button" id="replace-file" class="text">이 내용으로 목록 교체</button><button type="button" id="cancel-file" class="text">가져오기 취소</button></section>
 </article>
 <article><h2>학생과 수행 조건</h2><div class="fields"><label>이름 또는 별명 *<input name="name" maxlength="50" required value="${esc(project.name)}" placeholder="예: 탐구자"></label><label>학년 *<select name="grade">${['초등 1학년','초등 2학년','초등 3학년','초등 4학년','초등 5학년','초등 6학년','중등 1학년','중등 2학년','중등 3학년','고등학생'].map(x=>`<option ${project.grade===x?'selected':''}>${x}</option>`).join('')}</select></label><label>지역 *<input name="region" maxlength="100" required value="${esc(project.region)}" placeholder="예: 서울, 경기"></label><label>학생별 재료비 한도 (원, 선택)<input name="budget" type="number" min="0" max="10000000" step="1" value="${esc(project.budget)}" placeholder="미입력: ${Number(project.defaultSnapshot.budget).toLocaleString()}원"></label><label>준비 기간 (주)<input name="weeks" type="number" min="1" max="104" step="1" required value="${esc(project.weeks)}"></label><label>회당 수업 시간<input name="hoursPerSession" type="number" min="0.5" max="24" step="0.5" required value="${esc(project.hoursPerSession)}"></label><label>실험 장소 *<input name="location" maxlength="100" required value="${esc(project.location)}"></label><label>보유 장비·관찰 조건<textarea name="equipment" maxlength="1000" rows="2" placeholder="예: 현미경 없음, 매일 10분 관찰 가능">${esc(project.equipment)}</textarea></label></div><p id="condition-summary"></p><small>이름·지역은 화면과 저장에만 사용하며 AI 요청에서 제외합니다. 이 단계의 저장 위치는 현재 브라우저입니다.</small></article>
 <p id="error" role="alert"></p>
 <button class="primary" type="submit">주제 목록 확인하기 →</button>
 <article id="topic-review" hidden><h2>원본 주제 구분 확인</h2><p>줄마다 하나의 주제입니다. 잘못 구분됐다면 위 입력란을 수정해주세요. 확정 후 각 주제에 고유 ID가 부여됩니다.</p><ol id="topic-review-list"></ol><button id="confirm-topics" class="primary" type="button">이 목록으로 확정하기 →</button></article></form>
 <div class="project-tools">
 <details class="teacher-settings"><summary>선생님 기본 설정</summary><form id="settings-form"><p>저장한 기본값은 새 프로젝트에 적용합니다. 현재 프로젝트의 조건은 그대로 유지합니다.</p><div class="fields"><label>기본 재료비 (원)<input name="budget" type="number" min="0" max="10000000" step="1" required value="${esc(defaults.budget)}"></label><label>기본 준비 기간 (주)<input name="weeks" type="number" min="1" max="104" step="1" required value="${esc(defaults.weeks)}"></label><label>기본 회당 수업 시간<input name="hoursPerSession" type="number" min="0.5" max="24" step="0.5" required value="${esc(defaults.hoursPerSession)}"></label><label>기본 실험 장소<input name="location" maxlength="100" required value="${esc(defaults.location)}"></label></div><p>수업 빈도: 주 1회 (이번 버전 고정)</p><button class="primary" type="submit">기본 설정 저장</button><p id="settings-status" role="status"></p></form></details>
 <details class="teacher-settings"><summary>이 브라우저의 프로젝트 보관함</summary><div id="project-archive"></div></details>
 </div>`;
 const archive=root.querySelector('#project-archive');
 const archived=actions.listArchive();
 archive.innerHTML=archived.length?archived.map((p,i)=>`<p>${esc(p.name||'이름 미입력')} · ${esc(p.region||'지역 미입력')} · ${esc(p.createdAt?.slice(0,10)||'')} <button type="button" class="text" data-restore="${i}">불러오기</button></p>`).join(''):'보관된 프로젝트가 없습니다.';
 archive.querySelectorAll('[data-restore]').forEach(b=>b.onclick=()=>{if(confirm('현재 프로젝트를 보관하고 선택한 프로젝트를 불러올까요?'))actions.onRestore(archived[Number(b.dataset.restore)])});
 const form=root.querySelector('#ideas-form'),errors=root.querySelector('#error'),review=root.querySelector('#topic-review');let current={...project};let fileRequest=0;
 function sync(){
  const values=Object.fromEntries(new FormData(form));current={...current,...values};actions.onDraft(values);
  root.querySelector('#condition-summary').textContent=`적용 재료비 ${conditions(current).budget.toLocaleString()}원 · ${current.weeks}주 · 주 1회 ${current.hoursPerSession}시간 · ${current.location||'장소 미입력'}`;
  root.querySelector('#topic-count').textContent=`현재 ${splitTopics(current.ideas).length}개 / 최대 ${MAX_ORIGINAL_TOPICS}개`;
  review.hidden=true;
 }
 form.addEventListener('input',e=>{if(e.target.closest('#file-preview')||e.target.id==='file')return;sync()});
 form.onsubmit=e=>{e.preventDefault();sync();const problems=[...profileProblems(current),...topicProblems(current.ideas)];errors.textContent=problems.join('\n');if(problems.length)return;review.hidden=false;root.querySelector('#topic-review-list').innerHTML=splitTopics(current.ideas).map(x=>`<li>${esc(x)}</li>`).join('');review.scrollIntoView({block:'start',behavior:'smooth'})};
 root.querySelector('#confirm-topics').onclick=()=>{const problems=[...profileProblems(current),...topicProblems(current.ideas)];if(problems.length){errors.textContent=problems.join('\n');review.hidden=true;return}actions.onConfirm()};
 root.querySelector('#sample').onclick=()=>{if(form.elements.ideas.value.trim()&&!confirm('현재 원본 주제 목록을 예시로 교체할까요?'))return;form.elements.ideas.value=sampleIdeas.join('\n');sync()};
 const preview=root.querySelector('#file-preview'),text=root.querySelector('#extracted-text'),status=root.querySelector('#file-status');
 const cancel=()=>{fileRequest++;preview.hidden=true;text.value='';root.querySelector('#file').value=''};
 root.querySelector('#cancel-file').onclick=cancel;
 for(const [selector,append] of [['#append-file',true],['#replace-file',false]])root.querySelector(selector).onclick=()=>{
  if(!text.value.trim()){status.textContent='추출 결과가 비어 있습니다.';return}
  if(!append&&form.elements.ideas.value.trim()&&!confirm('현재 원본 주제 목록을 추출 내용으로 교체할까요?'))return;
  const original=form.elements.ideas.value;form.elements.ideas.value=append&&original.trim()?original+'\n'+text.value:text.value;cancel();sync();errors.textContent=topicProblems(current.ideas).join('\n');
 };
 root.querySelector('#file').onchange=async e=>{
  const file=e.target.files[0];if(!file)return;const version=++fileRequest;preview.hidden=false;text.value='';status.textContent='파일에서 텍스트를 추출하고 있습니다…';
  const buttons=[root.querySelector('#append-file'),root.querySelector('#replace-file')];buttons.forEach(b=>b.disabled=true);
  try{
   if(file.size>5000000)throw Error('파일은 5MB 이하로 선택해주세요.');
   const ext=file.name.split('.').pop().toLowerCase();let value;
   if(ext==='txt'){
    const bytes=await file.arrayBuffer();let extracted;
    try{extracted=new TextDecoder('utf-8',{fatal:true}).decode(bytes)}catch{extracted=new TextDecoder('euc-kr',{fatal:true}).decode(bytes)}
    if(!extracted.trim())throw Error('파일에 텍스트가 없습니다.');if(extracted.length>100000)throw Error('텍스트가 너무 깁니다. 주제 목록만 별도로 저장해주세요.');value={text:extracted,warnings:['줄 구분을 확인하고 주제 하나를 한 줄로 정리해주세요.']};
   }else{
    if(!['docx','hwpx','hwp'].includes(ext))throw Error('TXT·DOCX·HWPX·HWP 파일을 선택해주세요.');
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let offset=0;offset<bytes.length;offset+=32768)binary+=String.fromCharCode(...bytes.subarray(offset,offset+32768));
    const response=await fetch('/api/extract-topics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filename:file.name,content:btoa(binary)})});
    if(response.status===404)throw Error('문서 추출 서버가 필요합니다. 로컬 AI 서버를 실행하거나 TXT로 변환해주세요.');
    value=await response.json();if(!response.ok)throw Error(value.error||'문서를 추출하지 못했습니다.');
   }
   if(version!==fileRequest||!root.isConnected)return;
   text.value=value.text;status.textContent=value.warnings.join(' ');buttons.forEach(b=>b.disabled=false);
  }catch(err){if(version===fileRequest&&root.isConnected)status.textContent=err.message||'파일을 읽지 못했습니다. TXT로 변환 후 다시 시도해주세요.'}
 };
 root.querySelector('#settings-form').onsubmit=e=>{
  e.preventDefault();const data=Object.fromEntries(new FormData(e.target));const next={budget:Number(data.budget),weeks:Number(data.weeks),hoursPerSession:Number(data.hoursPerSession),sessionsPerWeek:1,location:data.location.trim()};
  const problems=settingsProblems(next),output=root.querySelector('#settings-status');if(problems.length){output.textContent=problems.join('\n');return}
  output.textContent=actions.onDefaults(next)?'새 프로젝트의 기본값을 저장했습니다. 현재 프로젝트는 바꾸지 않았습니다.':'저장하지 못했습니다. 브라우저 저장 공간을 확인해주세요.';
 };
 root.querySelector('#new-project').onclick=()=>{if(confirm('현재 프로젝트를 이 브라우저에 보관하고 새 프로젝트를 만들까요?'))actions.onNew()};
 // Rendering must not edit/save the original project.
 root.querySelector('#condition-summary').textContent=`적용 재료비 ${conditions(current).budget.toLocaleString()}원 · ${current.weeks}주 · 주 1회 ${current.hoursPerSession}시간`;
 root.querySelector('#topic-count').textContent=`현재 ${splitTopics(current.ideas).length}개 / 최대 ${MAX_ORIGINAL_TOPICS}개`;
}
