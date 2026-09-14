export async function api<T>(path:string,body?:unknown):Promise<T>{
 const response=await fetch(`/api${path}`,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!response.ok){let message=`Control plane returned ${response.status}`;try{const error=await response.json();message=typeof error.detail==='string'?error.detail:'Check the task inputs and limits.';}catch{}throw new Error(message);}
 return response.json();
}
export const money=(n:number|null|undefined)=>n==null?'Unavailable':`$${n.toFixed(n===0?2:8)}`;
export const shortModel=(s:string)=>s.includes('/')?s.split('/').slice(1).join('/'):s;
