'use client';
import {memo,useMemo} from 'react';
import {ReactFlow,Background,Handle,Position,type NodeProps,type Node,type Edge,BackgroundVariant} from '@xyflow/react';
import {ArrowUpRight,BrainCircuit,Check,CheckCheck,FlaskConical,GitBranch,Layers3,LoaderCircle,Orbit,ScanLine,ShieldCheck,Sparkles,Workflow,Wrench} from 'lucide-react';
import '@xyflow/react/dist/style.css';
import type {RunEvent} from '@/types';

const stages=[
 {id:'task',label:'Task',sub:'Request gateway',icon:ArrowUpRight,x:0,y:35},
 {id:'profiler',label:'Profile',sub:'Understand demand',icon:ScanLine,x:158,y:35},
 {id:'candidates',label:'Top-K recipes',sub:'Pareto selection',icon:Layers3,x:316,y:35},
 {id:'scheduler',label:'Schedule',sub:'Allocate intelligence',icon:BrainCircuit,x:474,y:35},
 {id:'inference',label:'Execute',sub:'W&B Inference',icon:Sparkles,x:632,y:35},
 {id:'evaluator',label:'Evaluate',sub:'Check actual quality',icon:ShieldCheck,x:790,y:35},
 {id:'result',label:'Result',sub:'Quality · cost · time',icon:CheckCheck,x:948,y:35},
 {id:'learning',label:'Learn',sub:'Update evidence',icon:GitBranch,x:158,y:197},
 {id:'compare',label:'Compare',sub:'Paired outcomes',icon:Workflow,x:316,y:197},
 {id:'shadow',label:'Shadow Lab',sub:'Isolated exploration',icon:FlaskConical,x:474,y:197},
 {id:'repair',label:'Repair',sub:'Target failed checks',icon:Wrench,x:632,y:197},
 {id:'weave',label:'Weave',sub:'Trace + evidence',icon:Orbit,x:948,y:197},
];
const links=[['task','profiler'],['profiler','candidates'],['candidates','scheduler'],['scheduler','inference'],['inference','evaluator'],['evaluator','result'],['evaluator','repair'],['repair','inference'],['result','weave'],['scheduler','shadow'],['shadow','compare'],['compare','learning']];
type StageData={stage:typeof stages[number];status:string;message:string};
type StageNode=Node<StageData,'stage'>;
const Stage=memo(function Stage({data}:NodeProps<StageNode>){const Icon=data.stage.icon;return <div className={`flow-node ${data.status} ${['shadow','compare','learning'].includes(data.stage.id)?'branch-node':''}`} data-testid={`node-${data.stage.id}`} data-status={data.status} title={data.message}>
 <Handle type="target" position={Position.Left}/><div className="node-top"><span className="node-icon"><Icon size={18}/></span>{data.status==='complete'?<Check size={13} className="node-check"/>:data.status==='active'?<LoaderCircle size={13} className="spin"/>:<span className="node-dot"/>}</div><strong>{data.stage.label}</strong><span className="node-sub">{data.stage.sub}</span><Handle type="source" position={Position.Right}/></div>;});
const nodeTypes={stage:Stage};

export function ExecutionGraph({events}:{events:RunEvent[]}){
 const latest=useMemo(()=>Object.fromEntries(events.map(e=>[e.stage,e])),[events]);
 const nodes:StageNode[]=useMemo(()=>stages.map(stage=>({id:stage.id,type:'stage',position:{x:stage.x,y:stage.y},data:{stage,status:latest[stage.id]?.status??'idle',message:latest[stage.id]?.message??'Awaiting execution'},draggable:false})),[latest]);
 const edges:Edge[]=useMemo(()=>links.map(([source,target])=>({id:`${source}-${target}`,source,target,type:'smoothstep',animated:latest[target]?.status==='active',style:{stroke:latest[target]?.status==='active'?'#9d88ff':latest[target]?.status==='complete'?'#415f7a':'#253043',strokeWidth:1.3,strokeDasharray:['shadow','compare','learning','weave'].includes(target)?'5 5':undefined},pathOptions:{borderRadius:14}})),[latest]);
 return <div className="execution-canvas" aria-label="Live execution graph"><ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{padding:.06}} minZoom={.4} maxZoom={1.4} nodesConnectable={false} elementsSelectable={false} panOnDrag zoomOnScroll={false} proOptions={{hideAttribution:false}}><Background variant={BackgroundVariant.Dots} color="#293146" gap={18} size={.8}/></ReactFlow><div className="graph-lane-label">LIVE EXECUTION</div><div className="graph-learning-label">CONTINUOUS IMPROVEMENT</div></div>;
}
