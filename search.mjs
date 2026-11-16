export const normalizeTitle = s => String(s).normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu,'');
const grams = s => new Set(Array.from({length:Math.max(0,s.length-1)},(_,i)=>s.slice(i,i+2)));
export function buildIndex(records) {
 return records.map(record=>({...record,normalized:normalizeTitle(record.title),grams:grams(normalizeTitle(record.title))}));
}
export function searchAwards(index, query, {includeGuidance=false,source='',limit=5}={}) {
 const q=normalizeTitle(query);if(q.length<2)return [];
 const g=grams(q);
 return index.filter(r=>(includeGuidance||r.record_type!=='지도논문')&&(!source||r.source===source)).map(r=>{
  const common=[...g].filter(x=>r.grams.has(x)).length;
  const exact=q===r.normalized;
  const substring=r.normalized.includes(q)||q.includes(r.normalized);
  const similarity=2*common/(g.size+r.grams.size||1);
  return {record:r,score:exact?3:substring?2+similarity:similarity,common,match:exact?'제목 일치 (공백·기호 제외)':substring?'제목 구절 포함':'제목 일부 표현 일치'};
 }).filter(x=>x.score>=2||(x.common>=2&&x.score>=0.12)).sort((a,b)=>b.score-a.score||Number(b.record.year)-Number(a.record.year)||a.record.id.localeCompare(b.record.id)).slice(0,limit);
}
