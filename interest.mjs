export const INTEREST_DOMAINS=['물리','화학','생물','산업 및 에너지','지구 및 환경'];
export function originalTopics(project){return (project.topics||[]).filter(t=>t.origin==='original').map(({id,originalText})=>({id,originalText,origin:'original'}))}
export function interestSourceKey(project){return JSON.stringify(originalTopics(project))}
export function confirmedInterest(project){const analysis=project.interestAnalysis;return analysis?.result?.confirmed&&analysis.sourceKey===interestSourceKey(project)&&!project.interestEditing&&!project.staleResults?.interest?analysis.result:null}
export function applyInterest(project,result,sourceKey){
 const history=[...(project.resultHistory||[])];if(project.interestAnalysis)history.push({kind:'interest',value:project.interestAnalysis,savedAt:new Date().toISOString()});
 if(sourceKey!==interestSourceKey(project)){history.push({kind:'interest-stale-response',value:{result,sourceKey}});return {...project,resultHistory:history}}
 return {...project,interestAnalysis:{result,sourceKey},interestDraft:null,interestEditing:!result.confirmed,resultHistory:history,staleResults:{...project.staleResults,interest:!result.confirmed,evaluation:!!project.aiEvaluation||project.staleResults?.evaluation,plan:!!project.selected||project.staleResults?.plan}};
}
export function editInterest(project,draft){return {...project,interestDraft:{...draft,sourceKey:interestSourceKey(project)},interestEditing:true,staleResults:{...project.staleResults,evaluation:!!project.aiEvaluation||project.staleResults?.evaluation,plan:!!project.selected||project.staleResults?.plan}}}
export function summaryOfInterests(rows,topics){
 const valid=new Set(topics.map(t=>t.id));const total=topics.length;
 return INTEREST_DOMAINS.map(domain=>{const ids=new Set(rows.filter(i=>i.domains.includes(domain)).flatMap(i=>i.source_topic_ids).filter(id=>valid.has(id)));return {domain,topic_count:ids.size,ratio:total?Math.round(ids.size*1000/total)/10:0}});
}
