import type {Observation} from '@/types';

export function recipeFrontier(observations:Observation[]){
 const groups=new Map<string,Observation[]>();
 for(const row of observations){
  if(row.cost==null||row.recipe_id.startsWith('auth-'))continue;
  const key=`${row.family}/${row.recipe_id}`;
  groups.set(key,[...(groups.get(key)??[]),row]);
 }
 const rows=[...groups.values()].map(group=>({
  recipe:group[0].recipe_id,family:group[0].family,samples:group.length,
  quality:group.reduce((s,r)=>s+r.quality,0)/group.length,
  cost:group.reduce((s,r)=>s+(r.cost??0),0)/group.length,
  latency:group.reduce((s,r)=>s+r.latency,0)/group.length,
 }));
 return rows.map(a=>({...a,frontier:!rows.some(b=>b.family===a.family&&b.quality>=a.quality&&b.cost<=a.cost&&b.latency<=a.latency&&(b.quality>a.quality||b.cost<a.cost||b.latency<a.latency))}));
}
