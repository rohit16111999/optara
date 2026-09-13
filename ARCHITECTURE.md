# Optara architecture

The backend owns execution state and all paid actions. The browser visualizes persisted facts; elapsed-time animation is the only client-generated execution measurement. SQLite transactions serialize spend reservations and event sequence numbers. Weave is the remote evidence layer; a Weave or MCP outage does not replace local control logic.

```mermaid
flowchart LR
  subgraph Browser[Next.js browser]
    User[Task + quality + budget + deadline] --> UI[Mission Control]
    Graph[React Flow graph + KPIs + result]
  end
  subgraph Backend[FastAPI control plane]
    Gateway[Validated gateway] --> Profile[Heuristic profiler]
    Profile --> Registry[Registry + family evidence]
    Registry --> TopK[Feasibility + Pareto + top K]
    TopK --> Scheduler[Recipe scheduler]
    Scheduler --> Cache{Validated cache?}
    Cache -- miss --> Guard[Transactional SpendGuard]
    Guard --> Inference[W&B inference adapter]
    Inference --> Evaluate[Reference tests or rubric judge]
    Evaluate -- failed and allowance remains --> Repair[Targeted repair]
    Repair --> Guard
    Evaluate --> Result[Best answer + SLA]
    Cache -- hit --> Result
    Result --> Events[Persisted events + SSE]
  end
  UI --> Gateway
  Events --> Graph
  Inference --> WB[W&B Serverless Inference]
  Evaluate -. judge / verifier also guarded .-> Guard
  Backend --> DB[(SQLite)]
  Events -. safe stage metadata .-> Weave[Weave trajectory]
```

```mermaid
flowchart TD
  Result[Final production answer] --> Observe[Observe non-cache recipe outcome]
  Observe --> Smooth[Beta prior + mean cost / latency]
  Smooth --> Future[Future scheduling evidence]
  Result --> Sample{8% sample or explicit request}
  Sample -- selected --> ShadowGuard[Separate shadow spend scope]
  ShadowGuard --> Alternative[Alternative recipe on same task]
  Alternative --> Evaluation[Same evaluator and constraints]
  Evaluation --> Pair[Paired quality / cost / latency / SLA]
  Pair --> Candidate[Versioned candidate / shadow policy]
  Candidate --> Gate{Enough unique pairs, quality safe, improvement supported?}
  Gate -- no --> Collect[Collect evidence or reject]
  Gate -- yes, explicit promotion --> Production[Production policy version]
  Production --> Future
  Pair --> Evidence[Weave shadow evaluation + comparison / policy trace]
```

Shadow never updates production output or its metrics. Only its `shadow_result` association and subsequent event history are added. Comparison tracing is a separate root linked by run IDs because serving has already finished. Historical policy versions remain inspectable after replacement.

```mermaid
flowchart LR
  Explicit[CLI / UI / marimo explicit experiment] --> Cap[Model count + task count + batch cap]
  Cap --> Discovery[Authenticated model registry]
  Discovery --> Calibration[Measure allowed recipe variants]
  Calibration --> Evidence[(Versioned observations)]
  Evidence --> Frontier[Per-family Pareto plots]
  Evidence --> Fixed[Freeze Always Cheap and Always Strong]
  Fixed --> Benchmark[Same task suite and allowed pool]
  Benchmark --> Compare[Cheap / Strong / adaptive Optara]
  Compare --> Reports[SQLite summaries + Weave EvaluationLogger]
  Reports --> Lab[marimo interactive analysis]
  Reports --> Export[Evidence JSON for Molab / ARIA]
```

## Module boundaries

| Layer | Owner | Contract |
|---|---|---|
| Gateway / jobs | `backend/app/main.py` | Typed requests, 2 workers, read APIs, SSE replay, interrupted-job recovery |
| Execution | `controller.py` | Recipe → guarded calls → evaluations → bounded repair → immutable serving metrics |
| Scheduling | `scheduler.py`, `pareto.py`, `history.py` | Empirical family/version estimates, uncertainty, feasible top K |
| Safety | `spend_guard.py`, `safe_python.py`, `cache.py` | Atomic reservations, bounded AST execution, confidence/version/freshness cache rules |
| Learning | `shadow.py`, `policy.py` | Distinct paired evidence, configurable gates, explicit version promotion |
| Persistence | `persistence.py` | SQLite WAL, documents, ordered events, cumulative spend |
| Integrations | `backend/integrations/` | W&B inference, Weave Calls/evaluations, MCP history, disabled optional adapters |
| Experiments | `benchmarks/`, `experiment_lab/` | Shared fixed suite, fair pool/constraints, interactive evidence analysis |
| MCP | `backend/mcp_server/server.py` | Small stdio interface to the existing HTTP backend; no second worker/database owner |

## Invariants and failure behavior

All model calls—including judging, verification, repair, calibration, and shadow—pass through one guard. Reservations are made before a network request; actual known cost settles the reservation. Unknown usage retains its reservation. Time limits use a monotonic clock. No inference occurs at import, startup, page render, or status polling.

Run IDs, modes, recipe versions, evaluator versions, policy versions, and shadow associations make evidence attributable. Simulation fixtures never call sponsor services or feed live estimates. A newer evaluator cannot reinterpret old observations as current evidence; past reports remain immutable.

The browser consumes SSE during execution and polls snapshot history afterward so late shadow/learning events remain visible. Reconnects use event sequence IDs; loading a running saved task does not await a never-ending response body. Failures surface an explicit blocked/miss state. Restart recovery marks incomplete jobs interrupted rather than silently replaying paid calls.

Secret-bearing settings are never serialized into traces. Credential lookup uses environment/settings or the standard W&B credential file. Redaction applies to task/output paths and trace postprocessing. Inference failures expose a bounded diagnostic, not raw provider response headers or authorization data.

## Production evolution

The deployment package preserves this architecture in one long-running Docker service: `scripts/serve.py` starts FastAPI on internal port 8000, waits for its health check, then exposes production Next.js on the host's `PORT`. Same-origin `/api` rewrites carry HTTP and SSE to FastAPI. Railway's persistent volume is intended to mount at `/data`, with `OPTARA_DB_PATH=/data/optara.db`; the saved spend ledger survives deployments. W&B credentials belong in the hosting secret environment, never the image or repository. `RAILWAY_PUBLIC_DOMAIN` supplies the allowed browser origin unless explicitly configured. The existing public app and its persisted real execution were verified. The final pass makes no hosting changes; the active demo database is `/data/optara-demo.db`.

The current process and SQLite design minimize demo failure modes. A production version would replace the in-memory worker set with a durable queue, make the control plane stateless, use managed relational persistence and a distributed atomic budget ledger, add isolated execution workers, and scope cache/policies by authenticated tenant. The provider and evaluator interfaces are explicit so multi-provider/regional execution can evolve without changing the frontend event contract. Held-out workload evaluation and stronger statistical promotion controls come before automatic policy deployment.

## Scientific analysis surface

Mission Control shows current execution decisions. `experiment_lab/optara_lab.py` explains their empirical basis through reactive source/namespace/family filters, overview cards, Pareto charts, recorded candidate decisions, paired shadow deltas, policy gates, and the latest benchmark. The lab reads a safe versioned snapshot, an uploaded export, or the local API. It never promotes policies or makes paid calls on load. Molab uses the same portable notebook and public-safe evidence, with a rendered session for GitHub previews; it is not a second serving backend.
