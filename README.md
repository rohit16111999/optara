# Optara

**Intelligence, Optimized.**

“Kubernetes schedules compute. Optara schedules AI intelligence.”

**GitHub:** [rohit16111999/optara](https://github.com/rohit16111999/optara) · **W&B:** [project](https://wandb.ai/models-student1155/optara) · **Weave:** [traces and evaluations](https://wandb.ai/models-student1155/optara/weave)

**Mission Control:** [public app](https://optara-production.up.railway.app) — verified through read-only browser QA on 2026-09-13. **Experiment & Intelligence Lab:** [open in Molab](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py). See [MOLAB.md](MOLAB.md) for preview/runtime boundaries and [VALIDATION.md](VALIDATION.md) for measured results.

**Mission Control shows what Optara decides now. marimo shows the empirical evidence that teaches Optara what to decide next.** The operational surface executes and traces requests; the scientific surface compares recipes, Pareto membership, paired shadows, policy gates, and honest baseline results.

Optara is an AI execution control plane. Give it a task, quality target, dollar budget, and deadline. It selects an execution recipe, evaluates the actual answer, repairs failed constraints within limits, and records evidence for future scheduling. A separate shadow path tests alternatives before a versioned policy can be promoted.

![Real Optara execution](screenshots/live-run.png)

## Run locally

Tested on Windows 11 with Python 3.12.14 and Node 22.22.2. Python 3.12–3.13, Node 22+, [uv](https://docs.astral.sh/uv/getting-started/installation/), and Chrome are required for the documented Windows setup and browser tests. The lockfiles pin the verified dependencies.

```powershell
.\setup.ps1
.\start.ps1
```

Open **http://127.0.0.1:3000**. API documentation: http://127.0.0.1:8000/docs. Ctrl+C stops both services, including their Windows child processes. Neither startup nor page refresh performs inference or calibration. Keep the services bound to localhost.

For a production frontend:

```powershell
node frontend/node_modules/next/dist/bin/next build frontend
.\start.ps1 -Production
```

For macOS/Linux, install with `uv sync --frozen --python 3.12` and `npm ci --prefix frontend`, then `node scripts/dev.mjs`. Use `.venv/bin/python` in place of the Windows Python path below. Cross-platform scripts are provided; the completed browser validation was on Windows.

## Secure W&B setup

```powershell
.\scripts\login.ps1
.venv\Scripts\python.exe -m scripts.verify_wandb
```

The login script prompts in a terminal with **hidden input**, verifies the key through W&B, and uses W&B's standard saved credential file. It never prints the key or writes it into the repository. Existing `WANDB_API_KEY`, `.env`, or standard W&B credentials are supported. `.env.example` lists variable names only; copying it is optional because defaults are safe and saved login works.

The verifier discovers real model IDs, makes one tiny paid `OPTARA_WANDB_OK` request, and reads its trace back from Weave. Default project: [models-student1155/optara](https://wandb.ai/models-student1155/optara). [Weave project](https://wandb.ai/models-student1155/optara/weave).

The UI's **Verify connections** performs read-only discovery and authentication checks. Inference and trace delivery become connected after a successful real execution. Network/account failures remain visible; the local UI and explicitly selected Simulation continue working.

## What is scheduled

A recipe includes an authenticated model ID, reasoning configuration, output token budget, verifier configuration, agent count, sequential execution, evaluator strategy, repair limit, and version. Focused, Deliberate, and Verified recipes change these dimensions. Verified recipes perform a second review; its findings inform the rubric judge and any required repair. Deterministic checks retain final authority where available.

This is more than model routing: different recipes on the same model incur different costs and yield different observed quality. Optara selects the whole execution plan and measures its outcome. It does not claim to have invented model routing.

The profiler classifies coding, math, extraction, structured transformation, classification, summarization, writing, and reasoning using deterministic heuristics. It identifies supported reference checks and freshness-sensitive tasks without a model call. Arbitrary prompts work; unrecognized semantics receive a labelled rubric estimate rather than invented ground truth.

## Scheduling and learning

1. Retrieve observations for the task family, execution mode, recipe version, and current evaluator version.
2. Exclude recipes whose expected cost or latency exceeds the request constraints. Unknown prices prevent paid execution.
3. Remove measured Pareto-dominated recipes: another recipe must have at least equal quality, at most equal cost and latency, and one strict improvement. Cold priors cannot eliminate untested recipes.
4. Retain the top K candidates (default 3). Choose the cheapest candidate whose conservative quality estimate meets the target. If none does, choose the best feasible compromise and explicitly show SLA risk.
5. Evaluate, persist the outcome, and update estimates. Production policy preferences break ties; they cannot bypass feasibility or the quality ordering.

Quality uses a Beta(1,1) prior with fractional scores: `(1 + sum(scores)) / (n + 2)`. Uncertainty is `min(0.5, 1.96 * sqrt(q*(1-q)/(n+3)))`. Cost and latency use observed means. These are practical small-sample heuristics, not calibrated guarantees. An unobserved recipe has quality 0.5 ± 0.5 and a clearly labelled 15-second latency prior. Cache hits do not improve model performance statistics.

## Evaluation, repair, and SLA

- Exact arithmetic and explicit references use exact comparisons.
- JSON uses JSON Schema and optional expected field values. Schema compliance alone proves only the supplied structural constraints.
- Supported Python exercises use human-authored behavioral tests in a bounded AST interpreter. There is no Python `exec`/`eval`, import, filesystem, network, reflection, or unrestricted generated-code execution. Unsupported syntax is an evaluator limitation with zero confidence. Passing five longest-consecutive cases does not prove O(n) complexity.
- Open-ended answers use a separate rubric judge, visibly labelled **Estimated quality**. Judge calls consume the same spend, time, and call limits. Self-reported answer confidence is not used as quality.

Quality passes at `score >= requested target`. SLA HIT requires quality, total token-based cost, and execution latency all to meet their constraints. Missing cost means SLA MISS. The execution timer ends when the answer and evaluation are ready; subsequent Weave upload and shadow work are reported separately and are not counted as serving latency.

Failed checks trigger a targeted repair prompt preserving correct parts and identifying the failed constraints. Repair can expand output allowance up to 2,048 tokens, subject to the central guard. Defaults permit one repair and five total model calls. If repair is worse or blocked, the best evaluated answer is retained with an honest SLA result.

## Safe cache

The cache uses the trimmed, case-preserving prompt, evaluation specification, quality target, complete recipe/version, evaluator version, and live/simulation mode. It does not merge case or internal whitespace. Only passing results with adequate evaluator confidence are stored, for 24 hours. Volatile/personalized freshness patterns disable reuse. Budget and deadline are rechecked against the zero-cost cached result; changed recipe or evaluator invalidates reuse. The form exposes **Reuse validated results** and every hit is visible in the result and trace.

## Shadow Lab and policy safety

Production returns its answer before optional shadow execution. A deterministic hash samples 8% of uncached requests by default; a completed run also exposes **Test a shadow recipe**. A separate spend scope evaluates an alternative on the same task and reference checks. One production run may contribute only one pair. An existing candidate's evidence batch is filled before exploration spreads to another candidate.

Paired quality, cost, latency, and SLA deltas are persisted. Production output, quality, spend, latency, and SLA are immutable. Candidate policies move through candidate/shadow/production/rejected versions. Promotion is an explicit, revalidated operation requiring at least five distinct production pairs, a lower quality-delta bound of at least −0.02, and a supported cost, latency (>0.01 seconds), or SLA improvement. Bounds use mean ± configured z times standard error; default z=1.96. Small correlated samples remain a limitation. No single run, LLM claim, or ARIA suggestion can promote a policy.

## Calibration and benchmark

Start Optara, then run:

```powershell
.venv\Scripts\python.exe -m scripts.calibrate --max-models 2 --max-cost 0.03 --tasks 6
.venv\Scripts\python.exe -m scripts.benchmark --max-models 2 --max-cost 0.03 --tasks 6
```

The six-task suite contains arithmetic, exact instructions, extraction/JSON, two Python exercises, and rubric-based reasoning. Calibration measures three recipe variants per model. The frontend's quick controls use three tasks; the CLI above exercises all six. No batch starts automatically. `--dry-run` explicitly selects isolated simulation fixtures and spends nothing.

Always Cheap fixes the recipe with the lowest observed whole-execution cost. Always Strong fixes the highest observed mean-quality recipe; quality ties are deterministic and do not imply any model is inherently strongest. Optara remains adaptive. All three use the same allowed recipe pool, task suite, target 0.90, budget, deadline, evaluator, and disabled cache. Reports contain mean quality, mean/median cost, mean latency, SLA rate, and cost per success. Calibration and evaluation reuse a tiny suite, so these are **in-sample demonstrations**, not general savings claims. Earlier experiments remain immutable when recipes/evaluators change.

See [VALIDATION.md](VALIDATION.md) for measured results, current versions, and verification links.

## Weave and MCP

Each live run creates a root Weave call with child operations for profiling, history, ranking, scheduling, cache, inference, evaluation, repair, and learning. Outputs include exact recipes, actual usage, calculated cost, evaluation method, timing, SLA, and scheduler rationale. The backend flushes and reads the root back before displaying **Trace recorded**. Logging failure does not destroy the served answer.

Real `weave.EvaluationLogger` evaluations record calibration and benchmark rows. Shadow comparisons record paired evaluation rows and a comparison/policy trace linked by production and shadow IDs. Shadow tracing is a separate post-result trajectory; it does not reopen or change the production trace.

W&B MCP supports authenticated project discovery, trace schema discovery, trace counts, and historical queries. It is independent of live scheduling. Reproduce the protocol/history checks with:

```powershell
.venv\Scripts\python.exe -m scripts.verify_connections
```

Optara's own stdio MCP server exposes `optimize_task`, `get_run_result`, `explain_recipe`, `get_policy_summary`, and `get_recent_performance`:

```powershell
.venv\Scripts\python.exe -m backend.mcp_server.server
```

Configure that executable, arguments, and repository working directory in any MCP client. Keep the HTTP backend running. `optimize_task` can spend money within its request budget; the other tools are read-only. Weave is initialized before tool registration and uses the installed SDK's supported `patch_fastmcp()` integration. Protocol stdout stays clean. Client/server distributed trace propagation is not claimed.

Official implementation references: [Inference API](https://docs.wandb.ai/inference), [model discovery](https://docs.wandb.ai/inference/api-reference/list-models), [token pricing](https://site.wandb.ai/pricing/tokens/), [Weave Calls](https://docs.wandb.ai/weave/guides/tracking/create-call), [evaluation logger](https://docs.wandb.ai/weave/guides/evaluation/evaluation_logger), [MCP integration](https://docs.wandb.ai/weave/guides/integrations/mcp).

## marimo / Molab experiment lab

```powershell
.\lab.ps1
.venv\Scripts\python.exe -m scripts.export_evidence --mode live --output data/evidence.json
```

Open http://127.0.0.1:2718. Select evidence namespace/family, compare recipe quality/cost/latency, inspect family-specific Pareto points, review policy versions and shadow pairs, and browse benchmark/run history. The controlled-experiment form only submits work on an explicit click. Its default is Simulation.

For Molab, [open the GitHub notebook preview](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py); the committed session provides rendered outputs. **Run it now** starts an interactive server when account access permits. See [MOLAB.md](MOLAB.md). The notebook defaults to the public-safe `data/evidence.json` snapshot, using the repository copy locally or GitHub remotely. Uploading an export also works without localhost or credentials. LIVE and SIMULATION are checked separately, including mismatched uploads.

The lab includes an overview, quality/cost and quality/latency charts, family-specific Pareto membership, recorded scheduler decisions, shadow deltas, policy confidence/gates, the latest benchmark, run history, and sponsor evidence. Historical reports remain available; the benchmark tab never combines incompatible report versions. Controlled experiments default to Simulation and require an explicit submit against the local backend. No page-load inference occurs.

Exact standalone local command:

```powershell
.venv\Scripts\python.exe -m marimo run experiment_lab/optara_lab.py --host 127.0.0.1 --port 2718 --headless --no-sandbox
```

## Sponsor mapping and optional access

| Integration | Real role | Current access boundary |
|---|---|---|
| W&B Serverless Inference | Authenticated model discovery and execution | Verified live |
| Weave | Full trajectories, evaluation datasets, shadow and MCP evidence | Verified remotely |
| W&B MCP | Project and trace/history queries | Authenticated tools verified |
| marimo / Molab | Reactive experiment analysis and controlled local execution | Local app verified; portable notebook/export |
| ARIA | Experiment scientist: evidence → proposed candidate → shadow gate | No verified callable account/API access; disabled |
| TypeSafe | Optional candidate/provider adapter | No supplied hackathon credential or API contract; disabled |
| CoreWeave Sandboxes | Optional isolated generated-code execution | No `CWSANDBOX_API_KEY` or runner access; bounded local fallback |

ARIA handoff: open the real Weave project/evaluations, supply the exported evidence, and ask ARIA (if enabled in your account) to identify expensive recipes at equal quality within each family. Request evidence counts and a proposed recipe, not direct production changes. Review suggestions and test them through Shadow Lab. No ARIA analysis or recommendation has been fabricated. Sandbox capability requires its separate [control-plane credentials and runner access](https://docs.coreweave.com/products/sandboxes/get-started); an inference key does not establish it.

## Configuration and spend

| Variable | Default |
|---|---:|
| `WANDB_ENTITY` / `WANDB_PROJECT` | `models-student1155` / `optara` |
| `WANDB_MCP_URL` | `https://mcp.withwandb.com/mcp` |
| `MAX_COST_PER_REQUEST` | $0.05 |
| `MAX_TOTAL_DEV_SPEND` | $2.00 persisted cumulative cap |
| `MAX_CALIBRATION_SPEND` / `MAX_BENCHMARK_SPEND` | $0.25 each |
| `MAX_SHADOW_SPEND` | $0.10 |
| `MAX_MODEL_CALLS_PER_REQUEST` / `MAX_REPAIRS_PER_REQUEST` | 5 / 1 |
| `SHADOW_EXPLORATION_RATE` / `TOP_K` | 0.08 / 3 |
| `POLICY_MIN_EVIDENCE` | 5 |
| `POLICY_QUALITY_TOLERANCE` / `POLICY_CONFIDENCE_Z` | 0.02 / 1.96 |
| `POLICY_MIN_LATENCY_IMPROVEMENT` | 0.01 seconds |
| `DRY_RUN_MODE` | false; true forces all execution to Simulation |
| `OPTARA_DB_PATH` | `data/optara.db` |

Every model call reserves conservatively estimated input/output spend in a SQLite transaction before execution. The guard enforces request, batch, scope, total-development, call-count, and monotonic-deadline limits. Known actual usage settles reservations; timeouts or missing usage retain uncertain reservations. No blind transport retries. Unknown authoritative prices block paid calls.

Displayed cost is actual provider token usage multiplied by documented **uncached list rates** in `data/pricing.json`, with source and verification date. It is not a billing receipt and does not assume provider cache discounts. Model identifiers come from authenticated discovery; models without verified pricing are displayed but not scheduled for paid calls.

## Tests and visual QA

With the app running:

```powershell
.\test.ps1
```

Normal tests use controlled fixtures; they do not spend inference credits. The suite covers Pareto rules, scheduling, isolation, cache/versioning, cost accounting, concurrent guards, evaluator boundaries, repair bounds, policy gates, API/SSE, and recovery. Playwright exercises the form, graph, result, errors, navigation, and responsive widths. Screenshots are in `screenshots/`; live and simulation are visibly labelled.

Opt-in paid checks:

```powershell
$env:OPTARA_LIVE_TEST='1'
.venv\Scripts\python.exe -m pytest -q -m live
Remove-Item Env:OPTARA_LIVE_TEST
.venv\Scripts\python.exe -m scripts.validate_live
```

The last command performs five small real task/shadow pairs and bounded cache checks. Run it intentionally; it is not part of ordinary tests. To scan source and local evidence without printing matched secrets:

```powershell
.venv\Scripts\python.exe -m scripts.secret_scan
```

## Architecture and limitations

Next.js supplies Mission Control, React Flow stages, Motion transitions, and Recharts analysis. FastAPI owns execution and SSE; SQLite stores documents, ordered events, and spend reservations. HTTPX isolates the inference adapter. No heavyweight queue, vector database, or agent framework is needed. See [ARCHITECTURE.md](ARCHITECTURE.md), [DEMO.md](DEMO.md), and [SUBMISSION.md](SUBMISSION.md).

This is a single-user demonstrator with two concurrent worker slots and an existing public demo deployment. Priority is recorded but does not implement a preemptive queue. The heuristic profiler does not add external retrieval, so current-events tasks are not grounded. Model/judge variance and small-sample policy bounds limit general claims. The AST evaluator deliberately supports a subset of Python. Historical traces contain task content and model output after credential redaction; use synthetic/public demo tasks. The public demo has no tenant authentication; its persisted $2 inference ledger bounds aggregate model spending. SQLite and origin checks are not a multi-tenant security boundary. Hosting remains unchanged in the final pass.

Production evolution: retain the typed gateway, recipe/guard contracts, and event schema while moving to stateless API services, durable queues, isolated worker pools, managed relational storage, distributed cache, multi-tenant spend ledgers, regional execution, and multiple provider adapters. Add workload-specific held-out evaluations, calibrated uncertainty, queue-aware deadlines, and authenticated policy approvals before production adoption.
