import test from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
import {buildIndex,searchAwards} from '../search.mjs';
const records=[{id:'1',title:'빛의 색에 따른 식물 성장',record_type:'학생',source:'서울',year:'2025'}, {id:'2',title:'(지도논문) 빛의 색에 따른 식물 성장',record_type:'지도논문',source:'전국',year:'2026'}, {id:'3',title:'식물 성장과 온도',record_type:'학생',source:'전국',year:'2026'}];
test('exact title matches despite whitespace; guidance excluded by default',()=>{const r=searchAwards(buildIndex(records),'빛의색에따른식물성장');assert.equal(r[0].record.id,'1');assert.ok(r.every(x=>x.record.record_type!=='지도논문'))});
test('source and guidance filters',()=>{const r=searchAwards(buildIndex(records),'빛의 색',{includeGuidance:true,source:'전국'});assert.equal(r[0].record.id,'2')});
test('no invented matches for empty or unrelated input',()=>{for(const q of ['','a','zzzzzzzz'])assert.deepEqual(searchAwards(buildIndex(records),q),[])});
test('uploaded data maintains identities and provenance',()=>{const d=JSON.parse(readFileSync(new URL('../data/awards.json',import.meta.url)));assert.equal(d.records.length,d.metadata.total);assert.equal(new Set(d.records.map(r=>r.source+':'+r.id)).size,d.metadata.total);assert.equal(d.records.filter(r=>r.source==='전국'&&r.record_type==='학생').length,1457);assert.equal(d.records.filter(r=>r.source==='전국'&&r.record_type==='지도논문').length,863);assert.equal(d.records.filter(r=>r.record_type==='확인 필요').length,8)});

test('regional snapshot is complete, searchable, and does not contain masked titles',()=>{
 const d=JSON.parse(readFileSync(new URL('../data/awards.json',import.meta.url)));
 const added=JSON.parse(readFileSync(new URL('../data/regional/2026-11-18.json',import.meta.url))).records;
 assert.equal(added.length,759);
 for(const r of added){assert.ok(!r.title.includes('**'));assert.ok(r.url.startsWith('https://'));assert.deepEqual(d.records.find(x=>x.source===r.source&&x.id===r.id),r);}
 const index=buildIndex(d.records);
 for(const source of ['경기','광주','인천','경남','경북','제주']){
  const r=added.find(r=>r.source===source);
  assert.ok(searchAwards(index,r.title,{source}).some(x=>x.record.id===r.id));
  assert.equal(d.records.filter(r=>r.source===source).length,d.metadata.sources[source]);
 }
 assert.equal(added.filter(r=>r.raw_record_type==='교원'&&r.record_type==='확인 필요').length,4);
});
