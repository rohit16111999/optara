# Optara validation and Definition of Done

Verified 2026-09-13 UTC. These results describe actual executions, not simulations or projected savings. The existing public deployment was verified read-only in the final pass. No hosting settings, deployments, or public inference were changed in this pass.

## Final local acceptance

| Requirement | Evidence / status |
|---|---|
| Backend unit and integration fixtures | 77 passed, 1 opt-in paid test skipped; two dependency deprecation warnings |
| Paid integration | Opt-in W&B test passed separately; final browser request below independently passed |
| Frontend production build | Next.js 16.3.5 production build and TypeScript passed |
| Existing Playwright suite | 6 passed in the final complete smoke suite (9.1 seconds), including simulation SSE, repair, shadow isolation, API errors and responsive navigation |
| Browser visual QA | Mission Control, live graph/result, Runs, Shadow Lab, Policies, Calibration, Benchmarks; responsive widths 1280, 1024, 390; screenshots in `screenshots/` |
| Scheduler and evaluator evidence | Three real candidate recipes; full model ID, selection reason, actual tokens, exact check, and actual-versus-target SLA visible |
| Inference and Weave | Final uncached browser proof below; execution read back from remote Weave |
| Repair | Historical real coding run passed five checks after one targeted repair |
| Cache | Real repeat returned zero executions and zero cost; version/mode/freshness rules covered by tests |
| Shadow isolation | Five real paired runs preserved production output, quality, cost, latency, and SLA |
| Policy gates | Five-pair evidence persisted; inferior candidate correctly remained unpromoted; promotion/version/rejection paths tested |
| W&B MCP | Authenticated project, schema, count, and history queries passed; Optara's five-tool stdio interface passed |
| Weave evaluations | Current calibration, benchmark, paired-shadow evaluation, comparison, and MCP traces remotely read back as finished without exceptions |
| marimo lab | Polished six-tab lab, overview cards, family Pareto charts, recorded scheduler decisions, paired deltas, policy gates and latest benchmark; safe exported evidence and rendered Molab preview prepared |
| ARIA / TypeSafe / Sandbox | Unavailable; disabled integrations and bounded local AST fallback reported truthfully |
| Secret scan / repository | No findings in source and local evidence scan; credentials, databases, caches, environments and build artifacts ignored |
| GitHub | Public repository pushed: https://github.com/rohit16111999/optara |
| Public deployment / public real run | Existing [https://optara-production.up.railway.app](https://optara-production.up.railway.app) verified: persisted real run, assets, favicon, SLA/evaluator/trace evidence, responsive widths and no browser console errors |

## Final local browser proof

Prompt: `Calculate 37 * 19. Return only the number.` Cache explicitly bypassed, Live W&B selected.

- Run: `9dbae5a2-aec1-4ff3-a35c-9282e6cf515f`
- Answer: **703**; deterministic quality **1.0**; **SLA HIT**.
- Usage: **108 input + 20 output = 128 tokens**.
- Cost: **$0.00000584**, computed from actual usage and documented uncached list rates.
- Serving latency: **0.563 seconds**; three candidate recipes; cache miss.
- Browser errors: **none**.
- [Remotely verified execution trace](https://wandb.ai/models-student1155/optara/r/call/01a098ad-631e-76a8-af46-c4f5b4f347e3).

An automatically sampled shadow ran after this result, in its separate budget and trajectory. It did not alter the serving metrics.

## Calibration and benchmark

Current recipes are version 2; current evaluator is version 2. Old reports remain immutable and are not silently mixed into current scheduling estimates.

Calibration `4cfb6d61-ed36-4a85-97c4-dfb2384664ed` measured 36 executions: two models, three recipe variants, six tasks. Total token-rate cost was **$0.00331281**. [Finished Weave evaluation](https://wandb.ai/models-student1155/optara/r/call/01a09884-1963-7b7d-ba76-714e3b0f847a).

Benchmark `69903978-956c-47a6-88a2-f5c2f809c664` measured 18 executions: six tasks and three strategies. Total cost was **$0.00058883**. All strategies used identical constraints, evaluator, allowed pool and disabled cache. [Finished Weave evaluation](https://wandb.ai/models-student1155/optara/r/call/01a0988c-fcd4-7a6f-85e0-197fa4fa7501).

| Strategy | Mean quality | Mean cost | Median cost | Mean latency | SLA hit rate | Cost / success |
|---|---:|---:|---:|---:|---:|---:|
| Always Cheap | 0.991667 | $0.0000334583 | $0.00000910 | 2.3412 s | 100% | $0.0000334583 |
| Always Strong | 0.991667 | $0.0000266867 | $0.00000910 | 1.4792 s | 100% | $0.0000266867 |
| Optara | 0.991667 | $0.0000379933 | $0.00000910 | 1.6092 s | 100% | $0.0000379933 |

**This sample does not demonstrate cost savings for Optara.** Calibration and comparison reuse a tiny suite; these are in-sample control-system demonstrations, not held-out generalization claims. Baseline labels describe selection rules, not assumed model superiority. Real repeated responses vary. Costs are calculated list-rate estimates, not billing receipts.

## Repair, shadow, and learning evidence

The [first real coding repair](https://wandb.ai/models-student1155/optara/r/call/01a0987a-6628-797b-bc20-738173ded78f) passed five behavioral cases after one repair: $0.00009673, 2.672 seconds, 1,291 tokens. This historical run predates evaluator v2 and is retained as repair evidence only. Supported behavioral tests do not prove asymptotic complexity.

Five distinct real math production/shadow pairs achieved quality 1.0 on both paths. The candidate's mean cost saving was **−$0.00001988** and mean latency saving **−0.95 seconds**, with no SLA improvement. Policy `0cfd28a3-7707-4ea1-82f9-75a5401a9f38` therefore stayed in shadow state, ineligible for promotion. A premature promotion attempt returned HTTP 409. No live promotion is fabricated.

[Paired comparison trace](https://wandb.ai/models-student1155/optara/r/call/01a0988b-67bb-7144-87e8-626a99a1c8b0), [shadow evaluation](https://wandb.ai/models-student1155/optara/r/call/01a0988b-67c5-7b00-b869-a7e40c655de5), and [instrumented Optara MCP call](https://wandb.ai/models-student1155/optara/r/call/01a09886-7c9d-7c27-88ef-464a68a9de87) were read back from Weave as finished without exceptions.

## Public acceptance and final lab checks

The existing public run `6c5a3d47-3791-4edc-bba5-d63523e21dae` used `openai/gpt-oss-20b`, bypassed cache, returned **703**, and passed deterministic evaluation at quality **1.0**. Actual usage was **108 input + 20 output = 128 tokens**, calculated cost **$0.00000584**, serving latency **0.586803 seconds**, and SLA **HIT** against quality 0.90, $0.003, and 45 seconds. Three candidate recipes and the scheduler's uncertainty warning remain visible.

[Public execution trace](https://wandb.ai/models-student1155/optara/r/call/01a098bc-7d84-7d38-a2f8-6a8276ae7b58).

The final pass loaded this saved request rather than buying another inference. Read-only Playwright checks passed for landing page, graph, model/token/evaluator/SLA evidence, trace link, static assets, favicon, navigation and responsive widths. Browser console errors: **none**. The only earlier resource error was the favicon, fixed before this pass; no hosting changes were made in the final pass.

Backend tests: **77 passed, 1 skipped**, two third-party deprecation warnings. Frontend: **production build and TypeScript passed**, including `/icon.svg`. Existing Playwright suite: **6 passed**. No new paid inference, calibration, or shadow batch was run in this final pass.

The marimo lab retains immutable real evidence and clearly separates namespaces. Its overview excludes authentication-only observations. Production counts refer to uncached serving observations, not calibration/benchmark/shadow calls. Policy confidence remains an evidence-count heuristic. Saved selected/rejected decisions are displayed directly; the lab does not invent or enact policy decisions. The exported snapshot contains no prompts, model outputs, or credentials. See [MOLAB.md](MOLAB.md) for public preview and interactive-runtime status.

ARIA: no callable capability in the authenticated W&B MCP inventory or present credential. TypeSafe AI: no hackathon API/SDK documentation or legitimate access in this environment. CoreWeave Sandbox: no `CWSANDBOX_API_KEY` or runner access. These adapters remain explicitly unavailable.
