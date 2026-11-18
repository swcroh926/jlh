export function duplicateTopics(project){
 const originals=(project.topics||[]).filter(t=>t.origin==='original');
 const generated=(project.generatedTopics||[]).map(t=>({id:t.id,originalText:t.originalText||t.title,origin:'generated'}));
 return [...originals,...generated].map(t=>({id:t.id,originalText:t.originalText,origin:t.origin,...Object.fromEntries(['question','target','method','measurement'].map(k=>[k,project.duplicateDetails?.[t.id]?.[k]||'']))}));
}
export function duplicateSourceKey(project){return JSON.stringify(duplicateTopics(project))}
export function currentDuplicate(project){
 const report=project.duplicateCheck;
 return report&&report.sourceKey===duplicateSourceKey(project)&&!project.staleResults?.duplicate&&project.duplicateManifest?.fingerprint===report.result.manifest.fingerprint?report.result:null;
}
export function applyDuplicate(project,result,sourceKey){
 const history=[...(project.resultHistory||[])];if(project.duplicateCheck)history.push({kind:'duplicate',value:project.duplicateCheck,savedAt:new Date().toISOString()});
 if(sourceKey!==duplicateSourceKey(project)){history.push({kind:'duplicate-stale-response',value:{result,sourceKey}});return {...project,resultHistory:history}}
 return {...project,duplicateCheck:{result,sourceKey},duplicateManifest:result.manifest,resultHistory:history,staleResults:{...project.staleResults,duplicate:false,evaluation:!!project.aiEvaluation||project.staleResults?.evaluation,plan:!!project.selected||project.staleResults?.plan}};
}
export function editDuplicate(project,details){return {...project,duplicateDetails:details,staleResults:{...project.staleResults,duplicate:true,evaluation:!!project.aiEvaluation||project.staleResults?.evaluation,plan:!!project.selected||project.staleResults?.plan}}}
export function setDuplicateManifest(project,manifest){
 const changed=project.duplicateCheck&&project.duplicateCheck.result.manifest.fingerprint!==manifest?.fingerprint;
 return {...project,duplicateManifest:manifest,staleResults:{...project.staleResults,duplicate:changed||project.staleResults?.duplicate,evaluation:changed?!!project.aiEvaluation||project.staleResults?.evaluation:project.staleResults?.evaluation}};
}
