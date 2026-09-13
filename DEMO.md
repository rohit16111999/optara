# Optara: three-minute demo

Before presenting, run `.\start.ps1 -Production` after building, and `.\lab.ps1` in another terminal. Open http://127.0.0.1:3000. Use **Live W&B**. The verified local database contains actual experiments; a fresh clone starts empty. On a fresh machine, use secure login, verification, calibration, and benchmark commands in README. Do not run calibration during the three-minute presentation.

| Time | Action and words |
|---|---|
| 0:00–0:20 | “Most AI applications spend intelligence statically. Easy and hard requests often receive the same model and reasoning strategy.” Point to quality, budget, and deadline. |
| 0:20–0:35 | “Kubernetes schedules compute. Optara schedules AI intelligence.” Point to the entire execution graph: recipes include reasoning, tokens, verification, and repair. |
| 0:35–1:15 | Click **Python algorithm**. Set quality **0.90**, budget **$0.02**, deadline **45 seconds**. Uncheck **Reuse validated results** for a real model call. Click **Run Optara**. Watch profiling, candidates, selection, inference, and evaluation. Read the actual scheduler reason, including uncertainty. |
| 1:15–1:40 | Inspect the answer and five behavioral checks. If a check fails, watch the bounded repair branch. A repair is conditional; never promise a failure or force a fake sponsor result. The persisted first real coding run is an authentic repair example available in Runs/Weave. |
| 1:40–2:00 | Show quality, token cost, measured latency, and SLA. Explain that HIT requires all three constraints. “Objective checks” means the supplied tests; it does not prove algorithmic complexity. For a rubric task, call the score estimated. |
| 2:00–2:25 | Open **Trace recorded**. Show the scheduler, inference, evaluator, repair if present, and saved metadata. Use the actual link in the current result. |
| 2:25–2:45 | Click **Test a shadow recipe**, then **Shadow Lab**. Show paired outcomes and immutable production metrics. Open **Policies**: evidence count and the promotion gate are real; collecting evidence or rejection is an honest outcome. |
| 2:45–3:00 | Show the measured **Benchmarks** table, then close: “Optara continuously learns how much intelligence each task deserves.” Avoid unqualified percentage-savings claims from six tasks. |

Optional follow-up: repeat an unchanged task with cache enabled to show zero-call reuse; open marimo to inspect the family-specific Pareto plot and compare the same persisted shadow/benchmark evidence.

The first real coding repair is [recorded in Weave](https://wandb.ai/models-student1155/optara/r/call/01a0987a-6628-797b-bc20-738173ded78f). It passed five tests after one repair, at 2.672 seconds and $0.00009673 in documented token-rate cost. It predates the evaluator-v2 correction; use it only to demonstrate that historical repair, not to represent current benchmark results.

If W&B is temporarily unavailable, show the saved real traces and reports. Simulation remains available for an explicitly labelled offline walkthrough; never present it as live sponsor inference.
