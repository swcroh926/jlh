export const sampleIdeas = ['빛의 색에 따라 새싹의 성장이 달라질까?', '종이 날개의 모양에 따른 낙하 시간 비교', '천연 소재에 따른 물의 여과 효과 비교'];
export function evaluate(ideas) {
 return ideas.map((title,i)=> {const scores=[78+i%3*3,75+i%4*2,86-i%3*4,82];return {id:i,title,scores,average:Math.round(scores.reduce((a,b)=>a+b,0)/4)} }).sort((a,b)=>b.average-a.average).slice(0,3);
}
export function parseIdeas(text){return text.split(/\r?\n/).map(x=>x.trim()).filter(Boolean)}
export const experiments=[{title:'예비 실험 · 측정 방법 확인',goal:'선택한 주제의 가설을 적고, 한 번에 바꿀 조건과 측정할 값을 정하세요.',steps:['독립 변수·종속 변수·통제 변수를 기록합니다.','소규모로 측정해 도구와 기록 방법을 확인합니다.','안전과 준비물을 선생님과 확인합니다.']},{title:'본 실험 · 조건별 비교',goal:'비교 조건을 동일하게 유지하고, 조건마다 반복 측정하세요.',steps:['비교군과 실험군을 준비합니다.','조건별로 3회 이상 측정하는 계획을 검토합니다.','측정값과 예상하지 못한 변화를 함께 기록합니다.']},{title:'확인 실험 · 결과 재검토',goal:'차이가 반복해서 나타나는지 확인하고 오차 원인을 살펴보세요.',steps:['이전 결과를 표로 정리합니다.','필요한 조건을 다시 측정합니다.','가설을 뒷받침하는 점과 해석의 한계를 적습니다.']}];
