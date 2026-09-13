# Optara

**Tagline:** Intelligence, Optimized.

**One-liner:** Optara is a self-improving AI execution control plane that dynamically allocates model capability, reasoning depth, verification, and repair budget to meet quality, cost, and latency targets.

## Problem

Static AI execution wastes resources: easy requests receive excessive reasoning, while harder requests receive insufficient verification. Comparing model prices alone misses the cost of judging, repair, failure, and latency. Observability shows what happened; applications still need a controller that uses that evidence to decide what happens next.

## Solution

Optara schedules complete execution recipes against a user's quality, cost, and latency constraints. It profiles tasks cheaply, retrieves empirical family-level history, filters the Pareto frontier, selects a small candidate set, and executes a guarded recipe. Actual output evaluation drives bounded targeted repair. A separate shadow path tests alternatives and supplies evidence for versioned, gated policy promotion.

Mission Control makes the loop visible through live backend events: task → profile → candidate recipes → schedule → execute → evaluate → result, with repair, Weave, and learning branches. Results distinguish objective reference checks from estimated rubric quality and calculate SLA across all three constraints.

## Technical architecture

Next.js / React / TypeScript / Tailwind, React Flow, Motion, Recharts, and Lucide power the frontend. FastAPI / Pydantic / HTTPX orchestrate execution. SQLite persists runs, events, recipes, observations, cache entries, paired shadows, policy versions, and an atomic spend ledger. A bounded Python AST interpreter safely evaluates supported coding exercises. The marimo notebook offers reactive evidence exploration and controlled experiments, with JSON import for Molab use.

See [ARCHITECTURE.md](ARCHITECTURE.md) for live, repair, shadow, learning, calibration, and frontend/backend diagrams.

## Sponsor usage

| Sponsor capability | Implemented use |
|---|---|
| W&B Serverless Inference | Real authenticated model discovery and guarded executions, with actual token counts and documented pricing |
| Weave | Remotely verified execution trajectories, benchmark/calibration evaluations, paired shadow evaluations, and supported MCP instrumentation |
| W&B MCP | Authenticated project and trace schema/count/history queries, independent of the serving path |
| marimo / Molab | Working local experiment lab and portable notebook with uploaded real evidence |
| ARIA | Disabled boundary; actual Weave evidence and documented analysis handoff ready when callable account access exists |
| TypeSafe | Disabled adapter pending actual hackathon documentation and credentials |
| CoreWeave Sandboxes | No credential/runner access; bounded local AST fallback, no fabricated sandbox execution |

## Difference from model routing

Optara's unit of optimization is a recipe, not a model name. Token allowance, reasoning level, verifier work, evaluation, and repair all change the resulting cost/quality/latency tradeoff. Historical runtime outcomes influence scheduling; shadow experiments test changes before a policy can affect production preferences. Existing routing research is acknowledged. No universal savings or autonomous statistical certainty is claimed.

## Two surfaces, one learning loop

**Mission Control shows what Optara decides now. marimo shows the empirical evidence that teaches Optara what to decide next.** Mission Control performs profiling, scheduling, real inference, evaluation, repair, SLA accounting, and tracing. The Experiment & Intelligence Lab reveals observed tradeoffs, Pareto membership, saved selected/rejected candidates, paired shadows, policy evidence and benchmark limitations. Safe exported evidence makes that analysis portable to Molab without private prompts or credentials.

## Demo and real results

The three-minute flow is in [DEMO.md](DEMO.md). Actual screenshots are in [screenshots/](screenshots/), and the completed validation audit with measured benchmark results is in [VALIDATION.md](VALIDATION.md). Live and simulation data are isolated. Benchmark failures remain visible, and old results are retained when implementation versions change.

**W&B project:** [models-student1155/optara](https://wandb.ai/models-student1155/optara)

**Weave:** [Optara traces and evaluations](https://wandb.ai/models-student1155/optara/weave)

**GitHub:** [rohit16111999/optara](https://github.com/rohit16111999/optara)

**Public Mission Control:** [Optara](https://optara-production.up.railway.app) — read-only browser QA verified.

**Experiment & Intelligence Lab:** [Molab GitHub preview](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py) · [local/runtime instructions](MOLAB.md).

**Measured results:** 77 backend tests passed, with the paid test separately verified. The final uncached local browser request returned 703 with quality 1.0, 128 tokens, $0.00000584 calculated cost, 0.563-second serving latency, and a remotely verified Weave trace. The 18-execution benchmark achieved equal mean quality (0.991667) and 100% SLA across all three strategies; Optara cost more on this small sample. See [VALIDATION.md](VALIDATION.md) for exact measurements and limitations.

## Limitations and future work

The current implementation is a single-user demonstrator with two worker slots and an existing public Mission Control deployment. Tiny in-sample benchmarks demonstrate control behavior, not population-level savings. The heuristic profiler, smoothed quality uncertainty, and approximate paired-policy bounds need validation on held-out workloads. Rubric scores are estimates. The safe interpreter supports a restricted Python subset and does not prove asymptotic complexity. Priority is recorded without a preemptive queue. Molab preview publication is distinct from an authenticated running cloud session. ARIA, TypeSafe, and external Sandboxes remain unavailable; no fabricated sponsor integration is claimed.

Future work includes held-out evaluation suites, calibrated uncertainty, richer capability discovery, authenticated multi-tenant controls, durable distributed workers, queue-aware deadlines, multi-provider recipes, and isolated full-language execution when sandbox access is available.
