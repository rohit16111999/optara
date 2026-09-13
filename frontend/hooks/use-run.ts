'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {api} from '@/lib/api';
import type {Run,RunEvent} from '@/types';

export function useRun(){
 const [run,setRun]=useState<Run|null>(null); const [events,setEvents]=useState<RunEvent[]>([]); const [busy,setBusy]=useState(false); const [error,setError]=useState<string|null>(null); const [elapsed,setElapsed]=useState(0);
 const stream=useRef<EventSource|null>(null); const started=useRef(0); const generation=useRef(0);
 useEffect(()=>()=>stream.current?.close(),[]);
 useEffect(()=>{if(!busy)return;const timer=setInterval(()=>setElapsed((performance.now()-started.current)/1000),100);return()=>clearInterval(timer);},[busy]);
 const load=useCallback(async(id:string)=>{stream.current?.close();generation.current++;setBusy(false);setError(null);const [result,raw]=await Promise.all([api<Run>(`/runs/${id}`),api<RunEvent[]>(`/runs/${id}/event-history`)]);setRun(result);setElapsed(result.total_latency);setEvents(raw);started.current=performance.now()-result.total_latency*1000;setBusy(!['completed','failed','interrupted'].includes(result.status));},[]);
 // Refresh persisted post-result shadow events, and active runs opened from history.
 useEffect(()=>{
  if(!run?.run_id)return;const id=run.run_id;const current=generation.current;let active=true;
  const timer=setInterval(async()=>{try{
   const [latest,history]=await Promise.all([api<Run>(`/runs/${id}`),api<RunEvent[]>(`/runs/${id}/event-history`)]);
   if(!active||current!==generation.current)return;
   setRun(latest);setEvents(history);
   if(['completed','failed','interrupted'].includes(latest.status)&&history.some(e=>e.stage==='done')){setBusy(false);setElapsed(latest.total_latency);}
  }catch{/* The connection banner reports service availability. */}},1500);
  return()=>{active=false;clearInterval(timer);};
 },[run?.run_id]);
 const submit=useCallback(async(payload:unknown)=>{
  stream.current?.close(); const current=++generation.current;setRun(null);setEvents([]);setError(null);setBusy(true);setElapsed(0);started.current=performance.now();
  try{
   const {run_id}=await api<{run_id:string}>('/runs',payload);
   if(current!==generation.current)return;
   const source=new EventSource(`/api/runs/${run_id}/events`);stream.current=source;
   source.onmessage=(message)=>{if(current!==generation.current)return;setError(null);const event=JSON.parse(message.data) as RunEvent;setEvents(previous=>previous.some(e=>e.sequence===event.sequence)?previous:[...previous,event]);if(event.result)setRun(event.result);if(event.stage==='done'){setBusy(false);setElapsed(event.result?.total_latency??0);source.close();}};
   source.onerror=async()=>{
    try{const result=await api<Run>(`/runs/${run_id}`);if(current!==generation.current)return;setRun(result);if(['completed','failed','interrupted'].includes(result.status)){setBusy(false);source.close();}else setError('Reconnecting to live events…');}
    catch{setError('Control plane disconnected. Your saved run will be available after reconnection.');setBusy(false);source.close();}
   };
  }catch(e){setError(e instanceof Error?e.message:'Unable to start run');setBusy(false);}
 },[]);
 const clear=useCallback(()=>{stream.current?.close();generation.current++;setRun(null);setEvents([]);setError(null);setBusy(false);setElapsed(0);},[]);
 return {run,events,busy,error,elapsed,submit,load,clear};
}
