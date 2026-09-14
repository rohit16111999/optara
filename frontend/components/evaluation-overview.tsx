'use client';

import {useMemo} from 'react';
import {ResponsiveContainer,ScatterChart,Scatter,XAxis,YAxis,CartesianGrid,Tooltip,Legend} from 'recharts';
import {recipeFrontier} from '@/lib/frontier';
import {money} from '@/lib/api';
import type {Candidate,Experiment,Mode,Observation,Run} from '@/types';

export function EvaluationOverview({observations,runs,recipes,experiments,mode,labUrl}:{observations:Observation[];runs:Run[];recipes:Candidate[];experiments:Experiment[];mode:Mode;labUrl:string}){
 const measured=useMemo(()=>observations.filter(o=>o.mode===mode&&!o.recipe_id.startsWith('auth-')),[observations,mode]);
 const rows=useMemo(()=>recipeFrontier(measured),[measured]);
 const recipeMap=new Map(recipes.map(r=>[r.recipe.recipe_id,r.recipe]));
 for(const run of runs)if(run.selected_recipe)recipeMap.set(run.selected_recipe.recipe_id,run.selected_recipe);
 const families=[...new Set(measured.map(o=>o.family))].sort();
 const coverage=new Map<string,number>();
 for(const run of runs){const e=run.final_evaluation;if(e){const key=`${e.evaluation_type} · ${e.deterministic?'objective':'estimated / limited'}`;coverage.set(key,(coverage.get(key)??0)+1);}}
 return <div className="evaluation-overview">
  <div className="kpi-grid">
   {[['Measured observations',measured.length],['Recipes evaluated',new Set(measured.map(o=>o.recipe_id)).size],['Task categories',families.length],['Completed experiment reports',experiments.filter(e=>e.status==='completed').length]].map(([label,value])=><div className="kpi-card cyan" key={label}><div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><p>{mode.toUpperCase()} · persisted evidence</p></div>)}
  </div>
  <p className="chart-note">Current evaluator evidence, grouped by task family and recipe. Pareto membership jointly considers quality, cost and latency within each family. Rows with unknown cost are excluded from the frontier. These small in-sample results do not establish universal cost savings.</p>
  <div className="evaluation-charts">{(['cost','latency'] as const).map(metric=><section className="panel" key={metric} aria-label={`Quality / ${metric} frontier`}><div className="panel-title"><h2>Quality / {metric} frontier</h2><span className="tag">{mode.toUpperCase()} · measured means</span></div>{rows.length?<div className="chart-container"><ResponsiveContainer width="100%" height="100%"><ScatterChart><CartesianGrid stroke="#222a3c" strokeDasharray="3 3"/><XAxis type="number" dataKey={metric} name={metric==='cost'?'Mean cost':'Mean latency'} unit={metric==='latency'?'s':undefined} stroke="#78839b" tickFormatter={v=>metric==='cost'?money(v):`${v}s`}/><YAxis type="number" dataKey="quality" name="Mean quality" domain={[0,1]} stroke="#78839b"/><Tooltip contentStyle={{background:'#131a29',border:'1px solid #313b52',borderRadius:10}}/><Legend/><Scatter data={rows.filter(r=>!r.frontier)} fill="#738199" name="Dominated within family"/><Scatter data={rows.filter(r=>r.frontier)} fill="#40c8c5" name="Pareto within family"/></ScatterChart></ResponsiveContainer></div>:<p className="quiet-placeholder">No measured recipe evidence in this namespace.</p>}</section>)}</div>
  <section className="panel"><div className="panel-title"><h2>Recipe performance</h2><span className="tag">Measured, not scheduler estimates</span></div><div className="table-scroll"><table><thead><tr>{['Recipe / Family','Model','Samples','Mean quality','Mean cost','Mean latency','Pareto'].map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map(r=><tr key={`${r.family}/${r.recipe}`}><td><strong>{recipeMap.get(r.recipe)?.name??r.recipe}</strong><small>{r.family} · {r.recipe}</small></td><td>{recipeMap.get(r.recipe)?.model_id??'Not in loaded registry'}</td><td>{r.samples}</td><td>{r.quality.toFixed(3)}</td><td>{money(r.cost)}</td><td>{r.latency.toFixed(3)}s</td><td><span className={`tag ${r.frontier?'green':'neutral'}`}>{r.frontier?'Frontier':'Dominated'}</span></td></tr>)}</tbody></table></div></section>
  <section className="panel"><div className="panel-title"><h2>Evaluator coverage</h2></div><p className="chart-note">Measured task families: {families.join(', ')||'None'}. Evaluator counts below describe final evaluations in the {runs.length} most recent loaded runs; they are not full-corpus coverage.</p><ul className="coverage-list">{[...coverage].map(([name,count])=><li key={name}>{name}: <strong>{count}</strong></li>)}</ul></section>
  <div className="method-note"><div><strong>Reproducible Evaluation Notebook</strong><p>Explore the existing evidence snapshot in marimo / Molab. The public preview includes rendered outputs; an interactive cloud session may require sign-in.</p><a className="weave-proof" href={labUrl} target="_blank" rel="noreferrer">OPEN REPRODUCIBLE EVALUATION NOTEBOOK ↗</a></div></div>
 </div>;
}
