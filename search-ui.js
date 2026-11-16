import {buildIndex,searchAwards} from './search.mjs';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let promise;
function data(){return promise??=fetch(new URL('./data/awards.json',import.meta.url)).then(r=>{if(!r.ok)throw Error('load');return r.json()}).then(d=>({...d,index:buildIndex(d.records)})).catch(e=>{promise=null;throw e})}
function safeLink(url){try{const u=new URL(url);return u.protocol==='https:'&&['www.science.go.kr','ssei.sen.go.kr'].includes(u.hostname)?u.href:null}catch{return null}}
export function mountSearch(root,queries=[]){
 if(!root)return;
 root.innerHTML=`<article class="award-search"><div class="eyebrow">실제 수집 자료</div><h2>비슷한 기존 작품 찾아보기</h2><p>제목의 단어·연속 글자를 비교합니다. AI 의미 검색이나 실험 방법의 중복 판정은 아닙니다.</p><p class="coverage" role="status">자료를 불러오는 중입니다…</p><label>검색할 아이디어<input class="award-query" maxlength="1000" placeholder="예: 식물 성장, 미세플라스틱"></label>${queries.length?`<div class="query-options">${queries.map((q,i)=>`<button type="button" data-query="${i}">${esc(q)}</button>`).join('')}</div>`:''}<div class="search-options"><label>출처<select class="award-source"><option value="">전국 + 서울</option><option>전국</option><option>서울</option></select></label><label class="check"><input type="checkbox" class="include-guidance">지도논문 포함</label><button type="button" class="primary search-button">유사 제목 검색</button></div><div class="award-results" aria-live="polite"></div></article>`;
 const input=root.querySelector('.award-query');input.value=queries[0]||'';
 let loaded;
 const run=()=>{
  const results=root.querySelector('.award-results');if(!loaded){results.textContent='자료를 먼저 불러와 주세요.';return}
  if(input.value.replace(/\s/g,'').length<2){results.textContent='두 글자 이상 입력해주세요.';return}
  const found=searchAwards(loaded.index,input.value,{source:root.querySelector('.award-source').value,includeGuidance:root.querySelector('.include-guidance').checked});
  results.innerHTML=found.length?found.map(({record:r,match})=>{const url=safeLink(r.url);return `<div class="award-result"><div class="row"><span class="tag">${esc(r.source)} · ${esc(r.year)} · ${esc(r.record_type)}</span><small>${esc(match)}</small></div><h3>${esc(r.title)}</h3><p>${esc(r.field)} · ${esc(r.award)}${r.record_type==='확인 필요'?` · 원본 유형: ${esc(r.raw_record_type)}`:''}</p>${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">원문 게시물 확인 ↗</a>`:''}</div>`}).join(''):'현재 보유 자료에서 유사 제목을 찾지 못했습니다. 더 짧은 핵심어로 검색해 보세요. 새로운 주제라는 뜻은 아닙니다.';
 };
 root.querySelector('.search-button').onclick=run;
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();run()}});
 root.querySelectorAll('[data-query]').forEach(b=>b.onclick=()=>{input.value=queries[Number(b.dataset.query)];run()});
 root.querySelector('.award-source').onchange=run;root.querySelector('.include-guidance').onchange=run;
 async function load(){try{
  loaded=await data();if(!root.isConnected)return;
  const m=loaded.metadata;
  root.querySelector('.coverage').textContent=`보유 ${m.total.toLocaleString()}건: 전국 ${m.sources['전국'].toLocaleString()}건 · 서울 ${m.sources['서울'].toLocaleString()}건. 지도논문 ${m.types['지도논문']}건은 기본 제외. 전국 전체 수집 완료를 의미하지 않습니다. 전국 미분류는 사용자 확인에 따라 학생으로 분류했습니다.`;
  if(input.value)run();
 }catch{
  if(!root.isConnected)return;
  root.querySelector('.coverage').innerHTML='자료를 불러오지 못했습니다. <button type="button" class="text retry-search">다시 시도</button>';
  root.querySelector('.retry-search').onclick=load;
 }}load();
}
