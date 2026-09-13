# /// script
# requires-python = ">=3.12"
# dependencies = ["marimo>=0.24", "httpx>=0.28", "pandas>=2.2", "altair>=5"]
# ///

import marimo

__generated_with = "0.24.2"
app = marimo.App(width="full", app_title="Optara · Experiment Lab")


@app.cell
def _():
    import json
    import httpx
    import pandas as pd
    import altair as alt
    import marimo as mo

    return alt, httpx, json, mo, pd


@app.cell
def _(mo):
    mo.md("""
    # Optara · Experiment Lab
    **Intelligence, Optimized.**

    Inspect empirical recipe tradeoffs, paired shadow outcomes, policy versions,
    and baseline comparisons. Live and simulation evidence remain separate.

    Run the local control plane first. On Molab, upload an exported evidence JSON
    to explore results without a localhost connection. Nothing on page load makes
    a paid inference request.
    """)
    return


@app.cell
def _(mo):
    mode_picker = mo.ui.dropdown(['live', 'simulation'], value='live', label='Evidence namespace')
    family_picker = mo.ui.dropdown(['all', 'coding', 'math', 'extraction', 'structured', 'reasoning', 'classification', 'writing'], value='all', label='Task family')
    refresh = mo.ui.run_button(label='Refresh evidence')
    evidence_upload = mo.ui.file(filetypes=['.json'], max_size=10_000_000, label='Upload exported evidence (Molab / offline)')
    mo.hstack([mode_picker, family_picker, refresh, evidence_upload], justify='start', gap=2)
    return evidence_upload, family_picker, mode_picker, refresh


@app.cell
def _(evidence_upload, httpx, json, mode_picker, refresh):
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
    label = 'SIMULATION · local fixtures, not model performance' if mode_picker.value == 'simulation' else 'LIVE · actual recorded model executions'
    mo.vstack([
        mo.callout(label, kind='warn' if mode_picker.value == 'simulation' else 'info'),
        mo.callout(lab_error, kind='warn') if lab_error else mo.md(f'**{len(filtered_rows)} observations** in the selected evidence scope.'),
    ])
    return (observations_df,)


@app.cell
def _(alt, mo, observations_df):
    if observations_df.empty:
        frontier_view = mo.md('### Recipe frontier\nNo calibration data yet. Run a controlled experiment below.')
        recipe_summary = observations_df
    else:
        recipe_summary = observations_df.groupby(['family','recipe_id'], as_index=False).agg(quality=('quality', 'mean'), cost=('cost', 'mean'), latency=('latency', 'mean'), samples=('quality', 'size'))
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
            color=alt.Color('pareto_frontier:N', title='Non-dominated'),
            tooltip=['family', 'recipe_id', 'quality', 'cost', 'latency', 'samples', 'pareto_frontier'],
        )
        frontier_view = mo.hstack([
            mo.ui.altair_chart(_base.encode(x=alt.X('cost:Q', title='Mean cost (USD)')).properties(title='Quality vs. cost', height=290)),
            mo.ui.altair_chart(_base.encode(x=alt.X('latency:Q', title='Mean latency (seconds)')).properties(title='Quality vs. latency', height=290)),
        ])
    mo.vstack([mo.md('### Calibration and Pareto comparison'), frontier_view, mo.ui.table(recipe_summary, selection=None)])
    return


@app.cell
def _(evidence, mo, pd):
    policy_rows = [{k: p.get(k) for k in ['version', 'task_family', 'status', 'evidence_count', 'confidence', 'creation_reason']} for p in evidence.get('policies', [])]
    shadow_rows = [{k: s.get(k) for k in ['production_run', 'production_recipe', 'shadow_recipe', 'production_quality', 'shadow_quality', 'production_cost', 'shadow_cost', 'production_latency', 'shadow_latency', 'status']} for s in evidence.get('shadow', [])]
    mo.vstack([
        mo.md('### Policy versions\nPromotion requires enough independent pairs, no material quality regression, and demonstrated objective improvement.'),
        mo.ui.table(pd.DataFrame(policy_rows), selection=None),
        mo.md('### Paired shadow experiments\nProduction output is immutable. These observations are recorded after the user-facing result.'),
        mo.ui.table(pd.DataFrame(shadow_rows), selection=None),
    ])
    return


@app.cell
def _(alt, evidence, mo, pd):
    benchmark_rows = []
    for _experiment in evidence.get('experiments', []):
        if _experiment.get('kind') == 'benchmark':
            for _name, _group in _experiment.get('groups', {}).items():
                benchmark_rows.append({'experiment': _experiment['id'], 'strategy': _name, **_group})
    benchmark_df = pd.DataFrame(benchmark_rows)
    benchmark_view = mo.md('Insufficient benchmark data.')
    if not benchmark_df.empty:
        benchmark_view = mo.ui.altair_chart(alt.Chart(benchmark_df).mark_bar().encode(x='strategy:N', y=alt.Y('mean_quality:Q', scale=alt.Scale(domain=[0, 1])), color='strategy:N', tooltip=['strategy', 'mean_quality', 'mean_cost', 'mean_latency', 'sla_hit_rate']).properties(height=260))
    mo.vstack([mo.md('### Always Strong / Always Cheap / Optara\nIdentical task suite, constraints, evaluators and disabled cache. Small in-sample comparisons are not general savings claims.'), benchmark_view, mo.ui.table(benchmark_df, selection=None)])
    return


@app.cell
def _(evidence, mo, pd):
    run_rows = [{k: r.get(k) for k in ['run_id', 'status', 'quality', 'total_cost', 'total_latency', 'sla_hit', 'cache_hit', 'trace_url']} for r in evidence.get('runs', [])]
    mo.vstack([mo.md('### Historical run exploration'), mo.ui.table(pd.DataFrame(run_rows), selection=None)])
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
