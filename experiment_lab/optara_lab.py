# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo>=0.24", "httpx>=0.28", "pandas>=2.2", "altair>=5"]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Optara · Experiment & Intelligence Lab")


@app.cell
def _():
    import json
    import httpx
    import pandas as pd
    import altair as alt
    import marimo as mo
    from pathlib import Path

    return Path, alt, httpx, json, mo, pd


@app.cell
def _(mo):
    mo.vstack([
        mo.Html('<style>body{font-family:system-ui,sans-serif}h1,h2,h3{font-family:inherit}.optara-hero{padding:28px 32px;border:1px solid #8370bc;border-radius:18px;background:linear-gradient(120deg,#151526,#252039);color:#f1edff}.optara-hero p{color:#c7beda}.optara-hero h1{font-size:30px;margin:10px 0}.optara-eyebrow{letter-spacing:.19em;font-size:11px;color:#bca6ff}marimo-stat{min-width:130px}</style>'),
        mo.Html('<div class="optara-hero"><span class="optara-eyebrow">OPTARA / INTELLIGENCE, OPTIMIZED.</span><h1>Experiment &amp; Intelligence Lab</h1><p>Kubernetes schedules compute. Optara schedules AI intelligence.</p><p>Mission Control shows what Optara decides now.<br>This lab shows the empirical evidence that teaches Optara what to decide next.</p></div>'),
        mo.md('[Mission Control](https://optara-production.up.railway.app) · [Weave evidence](https://wandb.ai/models-student1155/optara/weave) · [GitHub](https://github.com/rohit16111999/optara)\n\nExplore recorded outcomes without credentials or paid calls. Live execution remains an explicit action in Mission Control.'),
    ])
    return


@app.cell
def _(mo):
    mode_picker = mo.ui.dropdown(['live', 'simulation'], value='live', label='Evidence namespace')
    family_picker = mo.ui.dropdown(['all', 'coding', 'math', 'extraction', 'structured', 'reasoning', 'classification', 'writing'], value='all', label='Task family')
    refresh = mo.ui.run_button(label='Refresh evidence')
    source_picker = mo.ui.dropdown(['Saved demo evidence', 'Local API'], value='Saved demo evidence', label='Evidence source')
    evidence_upload = mo.ui.file(filetypes=['.json'], max_size=10_000_000, label='Upload exported evidence (Molab / offline)')
    mo.hstack([source_picker, mode_picker, family_picker, refresh, evidence_upload], justify='start', gap=2, wrap=True)
    return evidence_upload, family_picker, mode_picker, refresh, source_picker


@app.cell
def _(Path, evidence_upload, httpx, json, mode_picker, refresh, source_picker):
    refresh.value
    lab_error = None
    evidence = {'observations': [], 'policies': [], 'shadow': [], 'experiments': [], 'runs': []}
    if evidence_upload.value:
        try:
            evidence = json.loads(evidence_upload.value[0].contents)
            if evidence.get('mode') != mode_picker.value:
                lab_error = 'The uploaded evidence namespace does not match the selector.'
                evidence = {'observations': [], 'policies': [], 'shadow': [], 'experiments': [], 'runs': []}
        except (ValueError, KeyError, TypeError):
            lab_error = 'Invalid evidence JSON. Export with scripts/export_evidence.py.'
    elif source_picker.value == 'Saved demo evidence':
        try:
            _local = next((p for p in [Path('data/evidence.json'), Path('../data/evidence.json')] if p.is_file()), None)
            if _local:
                evidence = json.loads(_local.read_text(encoding='utf-8'))
            else:
                _response = httpx.get('https://raw.githubusercontent.com/rohit16111999/optara/main/data/evidence.json', timeout=15, follow_redirects=True)
                _response.raise_for_status()
                evidence = _response.json()
            if evidence.get('mode') != mode_picker.value:
                lab_error = 'The saved demo contains LIVE evidence only. Choose Local API or upload a matching simulation export.'
                evidence = {'observations': [], 'policies': [], 'shadow': [], 'experiments': [], 'runs': []}
        except (httpx.HTTPError, ValueError, OSError):
            lab_error = 'Saved evidence unavailable. Upload data/evidence.json from the repository; no localhost connection is needed.'
    else:
        try:
            with httpx.Client(base_url='http://127.0.0.1:8000', timeout=4) as _client:
                for _resource in evidence:
                    _response = _client.get(f'/api/{_resource}', params={'mode': mode_picker.value})
                    _response.raise_for_status()
                    evidence[_resource] = _response.json()
        except httpx.HTTPError:
            lab_error = 'Local API unavailable. Start Optara or upload an evidence export.'
    return evidence, lab_error


@app.cell
def _(evidence, family_picker, lab_error, mo, mode_picker, pd):
    filtered_rows = [r for r in evidence.get('observations', []) if not r.get('recipe_id','').startswith('auth-') and (family_picker.value == 'all' or r.get('family') == family_picker.value)]
    observations_df = pd.DataFrame(filtered_rows)
    scoped_runs = [r for r in evidence.get('runs', []) if family_picker.value == 'all' or (r.get('profile') or {}).get('task_family') == family_picker.value]
    scoped_shadow = [r for r in evidence.get('shadow', []) if family_picker.value == 'all' or r.get('family') == family_picker.value]
    scoped_policies = [r for r in evidence.get('policies', []) if family_picker.value == 'all' or r.get('task_family') == family_picker.value]
    _production = {r['run_id'] for r in filtered_rows if r.get('scope') == 'live'}
    label = 'SIMULATION · local fixtures, not model performance' if mode_picker.value == 'simulation' else 'LIVE · actual recorded model executions'
    mo.vstack([
        mo.callout(label, kind='warn' if mode_picker.value == 'simulation' else 'info'),
        mo.callout(lab_error, kind='warn') if lab_error else mo.md(f'**{len(filtered_rows)} observations** in the selected evidence scope.'),
        mo.hstack([
            mo.stat(len(filtered_rows), label='Recorded observations', bordered=True),
            mo.stat(len({r['recipe_id'] for r in filtered_rows}), label='Recipes evaluated', bordered=True),
            mo.stat(len(_production), label='Production executions', caption='Uncached observations', bordered=True),
            mo.stat(sum(r.get('status') == 'completed' for r in scoped_shadow), label='Completed shadow pairs', bordered=True),
            mo.stat(sum(r.get('status') == 'production' for r in scoped_policies), label='Production policies', caption=f'{len(scoped_policies)} policy versions', bordered=True),
        ], wrap=True),
        mo.md(f'Evidence snapshot: **{evidence.get("exported_at", "current local API")}** · Evaluator **{evidence.get("evaluator_version", "current")}**. Counts follow the selected family and namespace.'),
    ])
    return observations_df, scoped_policies, scoped_runs, scoped_shadow


@app.cell
def _(alt, evidence, mo, observations_df, scoped_runs):
    if observations_df.empty:
        frontier_view = mo.md('### Recipe frontier\nNo calibration data yet. Run a controlled experiment below.')
        recipe_summary = observations_df
    else:
        recipe_summary = observations_df.groupby(['family','recipe_id'], as_index=False).agg(quality=('quality', 'mean'), cost=('cost', 'mean'), latency=('latency', 'mean'), samples=('quality', 'size'))
        _models = {(r.get('selected_recipe') or {}).get('recipe_id'): (r.get('selected_recipe') or {}).get('model_id') for r in evidence.get('runs', [])}
        recipe_summary['model'] = recipe_summary['recipe_id'].map(_models).fillna('Not recorded')
        _records = recipe_summary.to_dict('records')
        _frontier = []
        for _a in _records:
            _dominated = any(
                _b['family'] == _a['family'] and _b['quality'] >= _a['quality'] and _b['cost'] <= _a['cost'] and _b['latency'] <= _a['latency']
                and (_b['quality'] > _a['quality'] or _b['cost'] < _a['cost'] or _b['latency'] < _a['latency'])
                for _b in _records if _b is not _a
            )
            _frontier.append(not _dominated)
        recipe_summary['pareto_frontier'] = _frontier
        _base = alt.Chart(recipe_summary).mark_circle(size=130).encode(
            y=alt.Y('quality:Q', scale=alt.Scale(domain=[0, 1])),
            color=alt.Color('pareto_frontier:N', title='Pareto frontier', scale=alt.Scale(domain=[True, False], range=['#8b6bdf','#63b8ba'])),
            tooltip=['family', 'recipe_id', 'model', 'quality', alt.Tooltip('cost:Q', format='.8f'), 'latency', 'samples', 'pareto_frontier'],
        )
        frontier_view = mo.hstack([
            mo.ui.altair_chart(_base.encode(x=alt.X('cost:Q', title='Mean cost (USD)')).properties(title='Quality vs. cost', height=290)),
            mo.ui.altair_chart(_base.encode(x=alt.X('latency:Q', title='Mean latency (seconds)')).properties(title='Quality vs. latency', height=290)),
        ])
    _decisions=[]
    for _run in scoped_runs:
        for _candidate in (_run.get('candidate_recipes') or []) + (_run.get('rejected_candidates') or []):
            _recipe=_candidate.get('recipe', {})
            _decisions.append({'run':_run['run_id'], 'recipe':_recipe.get('recipe_id'), 'model':_recipe.get('model_id'), 'selected':_candidate.get('selected'), 'reason':_run.get('scheduler_reason') if _candidate.get('selected') else _candidate.get('rejection_reason'), **{k:_candidate.get('metrics',{}).get(k) for k in ['expected_quality','expected_cost','expected_latency','observations']}})
    frontier_panel=mo.vstack([mo.md('### Recipe comparison\nMeasured family-level means. Pareto dominance is computed **within each family**, across quality, cost and latency. These means are distinct from the scheduler\'s smoothed estimates.'), frontier_view, mo.ui.table(recipe_summary, selection=None, show_column_summaries=False, format_mapping={'cost':'${:.8f}','latency':'{:.3f}s','quality':'{:.3f}'}), mo.accordion({'Recorded scheduler decisions':mo.vstack([mo.md('Actual selected and rejected candidates from saved runs; no reconstructed decisions.'),mo.ui.table(_decisions,selection=None,show_column_summaries=False,max_height=400)])})])
    return (frontier_panel,)


@app.cell
def _(mo, pd, scoped_policies, scoped_shadow):
    policy_rows = [{**{k: p.get(k) for k in ['version', 'task_family', 'status', 'evidence_count', 'confidence', 'creation_reason', 'promoted_at']}, 'eligible':p.get('comparison',{}).get('eligible'), 'gate_reason':p.get('comparison',{}).get('reason'), 'quality_lower_bound':p.get('comparison',{}).get('quality_delta_lower')} for p in scoped_policies]
    shadow_rows = []
    for _s in scoped_shadow:
        _row = {k:_s.get(k) for k in ['production_run','production_recipe','shadow_recipe','production_quality','shadow_quality','production_cost','shadow_cost','production_latency','shadow_latency','status']}
        for _metric in ['quality','cost','latency']:
            _p,_q = _s.get('production_'+_metric),_s.get('shadow_'+_metric)
            _row['shadow_minus_production_'+_metric]=_q-_p if _p is not None and _q is not None else None
        _row['gate_reason']=_s.get('promotion',{}).get('reason','Not assessed')
        _row['eligible']=_s.get('promotion',{}).get('eligible',False)
        shadow_rows.append(_row)
    policy_panel=mo.vstack([
        mo.md('### Policy versions\nPromotion requires enough independent pairs, no material quality regression, and demonstrated objective improvement.'),
        mo.callout('Unsafe automatic promotion is blocked. At least five distinct pairs, quality protection, and supported improvement are required. Promotion is explicit; this analysis surface never changes production policies. Confidence is an evidence-count heuristic, not a calibrated probability.', kind='info'),
        mo.ui.table(pd.DataFrame(policy_rows), selection=None, show_column_summaries=False),
    ])
    shadow_panel=mo.vstack([
        mo.md('### Paired shadow experiments\nProduction output is immutable. These observations are recorded after the user-facing result.'),
        mo.callout('Deltas are shadow minus production: positive quality is better; negative cost or latency is better. Eligibility comes from the stored policy gate, not this notebook.',kind='info'),
        mo.ui.table(pd.DataFrame(shadow_rows), selection=None, show_column_summaries=False, format_mapping={k:'${:.8f}' for k in ['production_cost','shadow_cost','shadow_minus_production_cost']}),
    ])
    return policy_panel, shadow_panel


@app.cell
def _(alt, evidence, mo, pd):
    benchmark_rows = []
    _reports=sorted([e for e in evidence.get('experiments', []) if e.get('kind')=='benchmark' and e.get('status')=='completed'],key=lambda e:e.get('created_at',''),reverse=True)
    for _experiment in _reports[:1]:
        if _experiment.get('kind') == 'benchmark':
            for _name, _group in _experiment.get('groups', {}).items():
                benchmark_rows.append({'experiment': _experiment['id'], 'strategy': _name, **_group})
    benchmark_df = pd.DataFrame(benchmark_rows)
    benchmark_view = mo.md('Insufficient benchmark data.')
    if not benchmark_df.empty:
        benchmark_view = mo.ui.altair_chart(alt.Chart(benchmark_df).mark_bar().encode(x='strategy:N', y=alt.Y('mean_quality:Q', scale=alt.Scale(domain=[0, 1])), color='strategy:N', tooltip=['strategy', 'mean_quality', 'mean_cost', 'mean_latency', 'sla_hit_rate']).properties(height=260))
    benchmark_panel=mo.vstack([mo.md('### Always Cheap / Always Strong / Optara\nLatest completed report; identical task suite, constraints, evaluators and disabled cache. Benchmark scope remains the full suite when the family filter changes.'),mo.callout('This small in-sample benchmark validates adaptive control behavior, not universal cost savings. Optara did not achieve a cost advantage in this recorded sample.',kind='warn'), benchmark_view, mo.ui.table(benchmark_df, selection=None, show_column_summaries=False, format_mapping={'mean_cost':'${:.8f}','mean_latency':'{:.3f}s','sla_hit_rate':'{:.0%}'}),mo.accordion({'Earlier benchmark reports':mo.ui.table([{'id':e['id'],'created_at':e.get('created_at'),'evaluator':e.get('evaluator_version'),'trace':e.get('evaluation_url')} for e in _reports],selection=None)})])
    return (benchmark_panel,)


@app.cell
def _(benchmark_panel, frontier_panel, mo, pd, policy_panel, scoped_runs, shadow_panel):
    run_rows = [{k: r.get(k) for k in ['run_id', 'status', 'quality', 'total_cost', 'total_latency', 'sla_hit', 'cache_hit', 'trace_url']} for r in scoped_runs]
    _runs_panel=mo.vstack([mo.md('### Run history\nSafe summaries and trace links. No private prompts or model outputs are needed for this demonstration.'), mo.ui.table(pd.DataFrame(run_rows), selection=None, show_column_summaries=False,format_mapping={'total_cost':'${:.8f}','total_latency':'{:.3f}s'})])
    _sponsors=mo.md('''### The evidence loop

| Capability | Role | Verified boundary |
|---|---|---|
| W&B Inference | Execute selected recipes | Real authenticated execution and actual token usage |
| Weave | Trajectories and evaluations | Remotely verified execution, repair, calibration, benchmark and shadow traces |
| W&B MCP | Historical evidence | Authenticated project, schema, count and trace queries |
| marimo / Molab | Experiment and policy analysis | This reactive analysis environment; portable safe evidence |
| ARIA | Propose evidence-based candidates | Experimental W&B UI evidence analysis used; not in serving path; no direct policy changes or verified programmatic integration |
| TypeSafe AI | Optional hackathon adapter | Hackathon access/documentation unavailable |
| CoreWeave Sandbox | Isolated evaluation runtime | Credential/runner unavailable; bounded local AST fallback |

[Open the real Weave project](https://wandb.ai/models-student1155/optara/weave). Mission Control executes; this lab explains the empirical learning loop.''')
    mo.ui.tabs({'Recipe frontier':frontier_panel,'Shadow comparisons':shadow_panel,'Policy learning':policy_panel,'Benchmark':benchmark_panel,'Run history':_runs_panel,'Sponsor evidence':_sponsors})
    return


@app.cell
def _(mo):
    experiment_form = mo.ui.dictionary({
        'kind': mo.ui.dropdown(['calibration', 'benchmark'], value='calibration', label='Experiment'),
        'mode': mo.ui.dropdown(['simulation', 'live'], value='simulation', label='Execution mode'),
        'max_models': mo.ui.number(start=1, stop=3, value=2, label='Maximum models'),
        'task_count': mo.ui.number(start=1, stop=6, value=3, label='Tasks'),
        'max_cost': mo.ui.number(start=.005, stop=.25, step=.005, value=.03, label='Maximum spend (USD)'),
    }).form(submit_button_label='Run controlled experiment', clear_on_submit=False)
    mo.vstack([mo.md('### Controlled execution\nOnly submitting this form starts an experiment. **Live mode can spend money** within the displayed cap. Requires the local Optara backend.'), experiment_form])
    return (experiment_form,)


@app.cell
def _(experiment_form, httpx, mo):
    mo.stop(experiment_form.value is None)
    _submitted = dict(experiment_form.value)
    _kind = _submitted.pop('kind')
    try:
        _response = httpx.post(f'http://127.0.0.1:8000/api/{_kind}', json=_submitted, timeout=30)
        _body = _response.json()
        experiment_message = f'Experiment queued: {_body["job_id"]}. Refresh evidence above to inspect progress.' if _response.status_code == 202 else f'Experiment not started: {_body.get("detail", "API error")}'
    except httpx.HTTPError:
        experiment_message = 'Local API unavailable. No experiment was started.'
    mo.callout(experiment_message, kind='info')
    return


if __name__ == "__main__":
    app.run()
