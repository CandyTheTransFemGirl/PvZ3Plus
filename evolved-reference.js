(function(){
const base='reference/decoded/36.0.95/';
let pending;
const load=()=>pending||(pending=Promise.all(['WaveDatabase','LevelLayoutDatabase','CombatDatabase','AlmanacConfig','RoadTripConfig'].map(n=>fetch(base+n+'.json').then(r=>{if(!r.ok)throw Error(n+' '+r.status);return r.json()}))).catch(e=>{pending=null;throw e}));
let generated;
async function generate(level){
const [w,l]=await load();
const all=await (generated||(generated=fetch(base+'PvZ3PlusLevels.json').then(r=>{if(!r.ok)throw Error('Generated levels unavailable');return r.json()}).catch(e=>{generated=null;throw e})));
const v=all[level];if(!v)throw Error('No generated reference for level '+level);
const b=w.Battles.find(x=>x.Id===v.battle_id),layout=l.LevelLayouts.find(x=>(x.Id??0)===v.layout_id);
return {...v,level,biome:b?.BoardVisualAlias,layout:layout?.Name,tiles:[...(layout?.PreSpawnedUnits||[]).map(x=>x.PreSpawnedUnit).filter(Boolean),...(b?.PreSpawnedUnits||[])],custom:typeof data!=='undefined'?data?.adventureLevels?.[level]:null};
}
window.PvZ3Reference={load,generate};
const button=document.createElement('button');button.textContent='Adventure reference generator';button.style.cssText='margin:12px';document.body.append(button);button.onclick=()=>{const d=document.createElement('dialog');d.style.cssText='max-width:90vw;max-height:85vh;overflow:auto;background:#172334;color:white';document.body.append(d);const n=document.createElement('input');n.type='number';n.min=1;n.value=typeof data!=='undefined'?Number(data?.level||0)+1:1;const seed=document.createElement('input');seed.type='number';seed.value=n.value;const out=document.createElement('pre');out.style.whiteSpace='pre-wrap';const go=document.createElement('button');go.textContent='Load generated level';const close=document.createElement('button');close.textContent='Close';close.onclick=()=>d.remove();d.append('Level ',n,go,close,out);go.onclick=async()=>{out.textContent='Loading reference…';try{const v=await generate(+n.value);out.textContent=JSON.stringify(v,null,2)}catch(e){out.textContent=e.message}};d.showModal();go.click()};
})();