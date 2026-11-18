// Run against: python3 -m backend.server --port 8012
// Requires Playwright and Chromium; calls no paid AI API.
import {createRequire} from 'node:module';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
const {chromium}=createRequire(import.meta.url)('playwright');
execFileSync(process.env.PYTHON||'python3',['-c',`from pathlib import Path
from backend.tests.test_documents import archive,DOC,HWPX
p=Path('.local/phase1-fixtures');p.mkdir(parents=True,exist_ok=True)
(p/'sample.docx').write_bytes(archive({'word/document.xml':DOC}))
(p/'sample.hwpx').write_bytes(archive({'Contents/section0.xml':HWPX}))`]);
const base=process.env.TEST_BASE_URL||'http://127.0.0.1:8012';
const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox']});
try{
 const context=await browser.newContext();const page=await context.newPage({viewport:{width:1440,height:1000}});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 let paidCalls=0;await page.route('**/api/evaluate',route=>{paidCalls++;return route.fulfill({status:503,json:{error:'이 브라우저 검증은 유료 AI를 호출하지 않습니다.'}})});
 let awardLoads=0;
 page.on('request', request=>{if(request.url().endsWith('/data/awards.json'))awardLoads++});
 await page.goto(base);
 await page.getByRole('heading',{name:'주제 입력',exact:true}).waitFor();
 assert.ok(await page.getByRole('textbox',{name:'원본 주제 목록'}).isVisible());
 assert.equal(await page.locator('#award-search .award-search').count(),0);
 assert.equal(awardLoads,0);
 assert.equal(await page.locator('#ideas-form [name=weeks]').inputValue(),'8');assert.equal(await page.locator('#ideas-form [name=budget]').inputValue(),'');
 await page.locator('#ideas-form [name=name]').fill('테스트 학생');await page.locator('[name=region]').fill('서울');await page.locator('#ideas-form [name=budget]').fill('0');
 await page.locator('#ideas-form [name=ideas]').fill('같은 주제\n같은 주제');await page.getByRole('button',{name:'주제 목록 확인하기'}).click();assert.match(await page.locator('#error').innerText(),/완전히/);
 const twenty=Array.from({length:20},(_,i)=>'원본 주제 '+(i+1)).join('\n');await page.locator('[name=ideas]').fill(twenty+'\n21번째 주제');await page.getByRole('button',{name:'주제 목록 확인하기'}).click();assert.match(await page.locator('#error').innerText(),/21개/);assert.equal((await page.locator('[name=ideas]').inputValue()).split('\n').length,21);
 await page.locator('[name=ideas]').fill('빛의  색과 식물 성장\n잎의 수 비교');
 const openSearch=page.getByRole('button',{name:'비슷한 작품 찾아보기'});
 await openSearch.click();
 await page.getByRole('heading',{name:'비슷한 작품 찾아보기',exact:true}).waitFor();
 assert.equal(await openSearch.getAttribute('aria-current'),'page');
 assert.equal(await page.locator('#ideas-form').isVisible(),false);
 await page.locator('.coverage').filter({hasText:'3,812'}).waitFor();
 assert.equal(awardLoads,1);
 await page.locator('.award-query').fill('식물');
 await page.getByRole('button',{name:'유사 제목 검색'}).click();
 await page.locator('#award-search .award-result').first().waitFor();
 await page.getByRole('button',{name:'주제 입력',exact:true}).click();
 assert.equal(await page.locator('#ideas').inputValue(),'빛의  색과 식물 성장\n잎의 수 비교');
 assert.equal(await page.locator('#award-search .award-search').count(),0);
 // TXT import is preview-only until explicit append/replace.
 await page.locator('#file').setInputFiles({name:'ideas.txt',mimeType:'text/plain',buffer:Buffer.from('다른 탐구 주제')});
 await page.locator('#extracted-text').filter({visible:true}).waitFor();assert.equal(await page.locator('[name=ideas]').inputValue(),'빛의  색과 식물 성장\n잎의 수 비교');
 await page.getByRole('button',{name:'가져오기 취소'}).click();assert.equal(await page.locator('[name=ideas]').inputValue(),'빛의  색과 식물 성장\n잎의 수 비교');
 // DOCX/HWPX fixtures use the real Python extraction endpoint.
 await page.locator('#file').setInputFiles('.local/phase1-fixtures/sample.docx');await page.waitForFunction(()=>document.querySelector('#extracted-text').value.includes('첫번째'));
 page.once('dialog',d=>d.dismiss());await page.getByRole('button',{name:'이 내용으로 목록 교체'}).click();assert.match(await page.locator('[name=ideas]').inputValue(),/빛의/);
 await page.getByRole('button',{name:'기존 목록에 추가'}).click();assert.match(await page.locator('[name=ideas]').inputValue(),/첫번째  주제/);
 await page.locator('#file').setInputFiles('.local/phase1-fixtures/sample.hwpx');await page.waitForFunction(()=>document.querySelector('#extracted-text').value.includes('생물 성장'));await page.getByRole('button',{name:'가져오기 취소'}).click();
 // Defaults do not overwrite the current project's zero budget/8-week snapshot.
 await page.locator('.teacher-settings').first().locator('summary').click();await page.locator('#settings-form [name=budget]').fill('90000');await page.locator('#settings-form [name=weeks]').fill('12');await page.locator('#settings-form [name=location]').fill('교실');await page.getByRole('button',{name:'기본 설정 저장'}).click();
 assert.equal(await page.locator('#ideas-form [name=budget]').inputValue(),'0');assert.equal(await page.locator('#ideas-form [name=weeks]').inputValue(),'8');
 await page.getByRole('button',{name:'주제 목록 확인하기'}).click();assert.equal(await page.locator('#topic-review-list li').count(),4);await page.getByRole('button',{name:'이 목록으로 확정하기'}).click();await page.locator('.eval-run').waitFor();
 let project=await page.evaluate(()=>JSON.parse(localStorage.getItem('jlh-project-v1')).project);assert.equal(project.topics.length,4);assert.equal(new Set(project.topics.map(t=>t.id)).size,4);assert.equal(project.defaultSnapshot.budget,300000);const ids=project.topics.map(t=>t.id);
 assert.equal(await page.locator('#award-search .award-search').count(),0);
 await page.locator('.select').first().click();await page.locator('#record').click();await page.locator('[data-note="0"][data-field="result"]').fill('기존 결과를 보존합니다');
 await page.reload();await page.getByRole('heading',{name:'주제 입력',exact:true}).waitFor();await page.locator('[data-step="3"]').click();assert.equal(await page.locator('[data-note="0"][data-field="result"]').inputValue(),'기존 결과를 보존합니다');
 await page.locator('[data-step="0"]').click();await page.locator('#ideas-form [name=weeks]').fill('9');await page.getByRole('button',{name:'주제 목록 확인하기'}).click();await page.getByRole('button',{name:'이 목록으로 확정하기'}).click();project=await page.evaluate(()=>JSON.parse(localStorage.getItem('jlh-project-v1')).project);assert.deepEqual(project.topics.map(t=>t.id),ids);assert.equal(project.notes[0].result,'기존 결과를 보존합니다');assert.ok(project.staleResults.plan);
 await page.locator('[data-step="2"]').click();assert.match(await page.locator('#app .notice').innerText(),/재검토/);
 // Archive and restore the old project when starting with edited defaults.
 await page.locator('[data-step="0"]').click();page.once('dialog',d=>d.accept());await page.locator('#new-project').click();assert.equal(await page.locator('#ideas-form [name=weeks]').inputValue(),'12');assert.match(await page.locator('#ideas-form [name=budget]').getAttribute('placeholder'),/90,000/);
 await page.locator('summary').filter({hasText:'프로젝트 보관함'}).click();page.once('dialog',d=>d.accept());await page.locator('[data-restore]').first().click();assert.equal(await page.locator('[data-note="0"]').count(),0);await page.locator('[data-step="3"]').click();assert.equal(await page.locator('[data-note="0"][data-field="result"]').inputValue(),'기존 결과를 보존합니다');
 await page.locator('[data-step="0"]').click();await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
 await mkdir('/workspace/deliverables',{recursive:true});await page.screenshot({path:'/workspace/deliverables/spec-phase1-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);assert.equal(paidCalls,0);
 await context.close();
 // A separate context verifies migration without discarding old notes/evaluation.
 const legacy=await browser.newContext();await legacy.addInitScript(()=>localStorage.setItem('jlh-project-v1',JSON.stringify({version:1,project:{step:3,name:'이전 학생',grade:'초등 5학년',budget:'50000',weeks:'4',ideas:'기존 주제',selected:{title:'기존 선택'},notes:{0:{result:'예전 기록'}},aiEvaluation:{result:{evaluations:[]}}}})));
 const old=await legacy.newPage();await old.goto(base);assert.equal(await old.locator('#ideas-form [name=weeks]').inputValue(),'4');assert.equal(await old.locator('#ideas-form [name=budget]').inputValue(),'50000');await old.locator('[name=region]').fill('경기');
 const saved=await old.evaluate(()=>JSON.parse(localStorage.getItem('jlh-project-v1')).project);assert.equal(saved.notes[0].result,'예전 기록');assert.ok(saved.aiEvaluation);await legacy.close();
 const privacy=await browser.newContext();const privatePage=await privacy.newPage();let requestBody;
 await privatePage.route('**/api/health',route=>route.fulfill({json:{configured:true,interests_available:true}}));
 await privatePage.route('**/api/evaluate',async route=>{requestBody=route.request().postDataJSON();const entry={idea_index:0,title:requestBody.ideas[0],average:75,passed:true,sources:[],uncertainties:['테스트 응답'],improvements:[],...Object.fromEntries(['originality','award_fit','feasibility','interest'].map(k=>[k,{score:75,reason:'테스트 근거'}]))};return route.fulfill({json:{evaluations:[entry],passed_count:1,top_three_indices:[0],next_step:'needs_more_candidates',threshold:70,search_mode:'lexical',model:'TEST-ONLY',rubric_version:'test',cached:false}})});
 await privatePage.goto(base);await privatePage.locator('#ideas-form [name=name]').fill('PRIVATE-NAME');await privatePage.locator('[name=region]').fill('PRIVATE-REGION');await privatePage.locator('[name=ideas]').fill('식물 성장 조건 비교');await privatePage.getByRole('button',{name:'주제 목록 확인하기'}).click();await privatePage.locator('#confirm-topics').click();await privatePage.locator('.interest-manual').click();await privatePage.locator('.interest-uncertainties').fill('초기 입력 단계 회귀검증: 관심사 미정');await privatePage.locator('.interest-confirm').click();await privatePage.locator('.duplicate-lexical').click();await privatePage.locator('.duplicate-results .duplicate-result').first().waitFor();await privatePage.locator('.eval-run:not([disabled])').waitFor();await privatePage.locator('.eval-run').click();await privatePage.locator('.eval-results .award-result').waitFor();
 assert.equal(requestBody.budget,300000);assert.equal(requestBody.hoursPerSession,3);assert.equal(requestBody.location,'학원');assert.ok(!('name' in requestBody));assert.ok(!('region' in requestBody));
 await privatePage.locator('[data-step="0"]').click();await privatePage.locator('#ideas-form [name=hoursPerSession]').fill('2');await privatePage.getByRole('button',{name:'주제 목록 확인하기'}).click();await privatePage.locator('#confirm-topics').click();assert.match(await privatePage.locator('.eval-results .notice').innerText(),/재평가 필요/);assert.equal(await privatePage.locator('.eval-select').count(),0);await privacy.close();
 console.log('PASS: new defaults, 0 budget, required profile, 20-topic limit, duplicates, TXT preview/cancel, DOCX/HWPX import, confirmation IDs, defaults isolation, notes restoration, stale plan, project archive, migration, mobile, privacy whitelist, stale evaluation; 0 provider API calls.');
}finally{await browser.close()}
