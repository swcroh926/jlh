// Phase 1: input/default rules. Existing evaluation is deliberately unchanged.
export const MAX_ORIGINAL_TOPICS = 20;
export const DEFAULT_SETTINGS = Object.freeze({budget:300000,weeks:8,sessionsPerWeek:1,hoursPerSession:3,location:'학원'});
export function id(){return globalThis.crypto.randomUUID()}
export function createProject(settings=DEFAULT_SETTINGS){
 return {id:id(),step:0,name:'',grade:'초등 5학년',region:'',budget:'',weeks:String(settings.weeks),sessionsPerWeek:1,hoursPerSession:String(settings.hoursPerSession),location:settings.location,equipment:'',ideas:'',topics:[],confirmedIdeas:null,selected:null,notes:{},defaultSnapshot:{...settings},staleResults:{},resultHistory:[],createdAt:new Date().toISOString()};
}
export function migrateProject(saved){
 if(!saved||typeof saved!=='object'||Array.isArray(saved))return createProject();
 // Never substitute newly edited teacher defaults into an older project.
 const p={...createProject(DEFAULT_SETTINGS),...saved};
 p.defaultSnapshot=saved.defaultSnapshot||{...DEFAULT_SETTINGS};
 if(!Object.hasOwn(saved,'location'))p.location='';
 p.topics=Array.isArray(saved.topics)?saved.topics:[];p.resultHistory=Array.isArray(saved.resultHistory)?saved.resultHistory:[];
 p.staleResults=saved.staleResults||{};
 if(!Array.isArray(p.topics)||!p.topics.length)p.confirmedIdeas=null;
 return p;
}
export function splitTopics(text){return String(text).split(/\r?\n/).map(x=>x.trim()).filter(Boolean)}
export function topicProblems(text){
 const rows=splitTopics(text),errors=[];
 if(rows.length<1||rows.length>MAX_ORIGINAL_TOPICS)errors.push(`원본 주제는 1~${MAX_ORIGINAL_TOPICS}개여야 합니다. 현재 ${rows.length}개이며 자동으로 잘라내지 않습니다.`);
 const seen=new Map();
 rows.forEach((title,i)=>{if(seen.has(title))errors.push(`${i+1}번 주제는 ${seen.get(title)+1}번과 완전히 같습니다. 확인 후 직접 수정해주세요.`);else seen.set(title,i);if(title.length<2||title.length>500)errors.push(`${i+1}번 주제는 2~500자로 입력해주세요.`)});
 return errors;
}
export function conditions(project){
 return {budget:project.budget===''||project.budget==null?Number(project.defaultSnapshot.budget):Number(project.budget),weeks:Number(project.weeks),sessionsPerWeek:1,hoursPerSession:Number(project.hoursPerSession),location:project.location,equipment:project.equipment||''};
}
export function profileProblems(p){
 const errors=[];if(!p.name.trim())errors.push('이름 또는 별명을 입력해주세요.');if(!p.grade.trim())errors.push('학년을 선택해주세요.');if(!p.region.trim())errors.push('지역을 입력해주세요.');if(!p.location.trim())errors.push('실험 장소를 확인해주세요.');
 for(const [key,label,min,max] of [['budget','재료비',0,10000000],['weeks','준비 기간',1,104],['hoursPerSession','회당 수업 시간',0.5,24]]){
  const v=conditions(p)[key];if(!Number.isFinite(v)||v<min||v>max||(key!=='hoursPerSession'&&!Number.isInteger(v)))errors.push(`${label} 입력 범위를 확인해주세요.`);
 }
 return errors;
}
export function settingsProblems(s){
 return profileProblems({...createProject(s),name:'설정',region:'설정',budget:String(s.budget)});
}
function signature(p){return JSON.stringify([p.ideas,p.grade,conditions(p)])}
export function applyDraft(project,patch){
 const next={...project,...patch};
 if(project.ideas!==next.ideas)next.confirmedIdeas=null;
 if(signature(project)!==signature(next)){
  next.staleResults={...project.staleResults,evaluation:!!project.aiEvaluation||project.staleResults?.evaluation,plan:!!project.selected||project.staleResults?.plan,interest:project.ideas!==next.ideas||project.staleResults?.interest,duplicate:project.ideas!==next.ideas||project.staleResults?.duplicate};
 }
 return next;
}
export function confirmTopics(project){
 const errors=[...profileProblems(project),...topicProblems(project.ideas)];if(errors.length)throw Error(errors.join('\n'));
 const old=project.topics||[];
 return {...project,topics:project.ideas.split(/\r?\n/).filter(line=>line.trim()).map(raw=>old.find(t=>t.originalText===raw)||{id:id(),originalText:raw,origin:'original'}),confirmedIdeas:project.ideas};
}
export function evaluationKey(project){return JSON.stringify([project.ideas,project.grade,conditions(project)])}
export function evaluationPayload(project,{equipment,interests,threshold}){
 const c=conditions(project);
 // A whitelist: name and region are intentionally never sent to the model.
 return {ideas:splitTopics(project.ideas),grade:project.grade,...c,equipment,interests,threshold};
}
