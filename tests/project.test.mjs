import test from 'node:test';import assert from 'node:assert/strict';
import {DEFAULT_SETTINGS,createProject,migrateProject,conditions,topicProblems,profileProblems,applyDraft,confirmTopics,evaluationPayload,evaluationKey,settingsProblems} from '../project.mjs';
const ready=()=>({...createProject(),name:'이름',region:'서울',ideas:'원래  표현을  지킬까?\n식물 성장 비교'});
test('new defaults apply only to newly created projects, zero budget is intentional',()=>{
 const a=createProject();const changed={...DEFAULT_SETTINGS,budget:90000,weeks:12,location:'교실'};const b=createProject(changed);
 assert.equal(conditions(a).budget,300000);assert.equal(a.weeks,'8');assert.equal(conditions(b).budget,90000);assert.equal(a.defaultSnapshot.location,'학원');assert.equal(conditions({...a,budget:'0'}).budget,0);assert.equal(conditions({...a,budget:''}).budget,300000);
});
test('old projects retain budget, weeks, notes, topics over the cap, and previous evaluation',()=>{
 const old={name:'old',budget:'50000',weeks:'4',ideas:Array.from({length:22},(_,i)=>'주제'+i).join('\n'),notes:{0:{result:'기록'}},aiEvaluation:{result:{}}};const p=migrateProject(old);
 assert.equal(p.budget,'50000');assert.equal(p.weeks,'4');assert.equal(p.ideas,old.ideas);assert.deepEqual(p.notes,old.notes);assert.equal(p.confirmedIdeas,null);assert.equal(p.location,'');assert.ok(topicProblems(p.ideas).length);
});
test('accepts 20 topics, rejects 21 without truncation and reports only exact duplicates',()=>{
 const text=Array.from({length:20},(_,i)=>'주제'+i).join('\n');assert.deepEqual(topicProblems(text),[]);assert.ok(topicProblems(text+'\n추가 주제').length);assert.match(topicProblems('주제 하나\n주제 하나').join(' '),/완전히/);assert.deepEqual(topicProblems('주제 하나\n주제하나'),[]);
});
test('confirmation assigns stable IDs and keeps original expression',()=>{
 let p=confirmTopics(ready());const ids=p.topics.map(t=>t.id);assert.equal(new Set(ids).size,2);assert.equal(p.topics[0].originalText,'원래  표현을  지킬까?');p=confirmTopics({...p,name:'다른 별명'});assert.deepEqual(p.topics.map(t=>t.id),ids);
});
test('required fields and condition ranges',()=>{
 assert.ok(profileProblems(createProject()).length);assert.equal(profileProblems(ready()).length,0);assert.ok(profileProblems({...ready(),hoursPerSession:'0'}).length);assert.ok(settingsProblems({...DEFAULT_SETTINGS,weeks:0}).length);
});
test('condition changes flag previous results but preserve old notes and selection',()=>{
 const p={...confirmTopics(ready()),aiEvaluation:{result:{average:80}},selected:{title:'기존 선택'},notes:{0:{result:'원본'}}};const next=applyDraft(p,{budget:'0'});
 assert.ok(next.staleResults.evaluation);assert.ok(next.staleResults.plan);assert.equal(next.selected,p.selected);assert.deepEqual(next.notes,p.notes);assert.notEqual(evaluationKey(p),evaluationKey(next));assert.equal(evaluationKey(p),evaluationKey(applyDraft(p,{name:'새 이름',region:'경기'})));
});
test('AI whitelist includes effective budget and conditions but never name or region',()=>{
 const p=ready();const body=evaluationPayload(p,{equipment:'전자저울',interests:'식물',threshold:70});assert.equal(body.budget,300000);assert.equal(body.hoursPerSession,3);assert.equal(body.location,'학원');assert.ok(!('name'in body));assert.ok(!('region'in body));assert.equal(evaluationPayload({...p,budget:'0'},{equipment:'',interests:'',threshold:70}).budget,0);
});

test('raw leading/trailing spaces are retained in confirmed original topics',()=>{
 const p=confirmTopics({...ready(),ideas:'  학생의 원래 표현  \n다른 주제'});assert.equal(p.topics[0].originalText,'  학생의 원래 표현  ');
});
