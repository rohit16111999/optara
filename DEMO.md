# Optara: three-minute judge demo

Open [Mission Control](https://optara-production.up.railway.app) and the [Molab Experiment & Intelligence Lab](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py). For a guaranteed local interactive lab, run `./lab.ps1` and open http://127.0.0.1:2718. Molab preview/runtime instructions are in [MOLAB.md](MOLAB.md). No calibration is needed during the presentation.

**Primary fresh prompt:** `Calculate 43 * 17. Return only the number.` Expected answer: **731**.

**Backup prompt:** `Implement a Python function longest_consecutive(nums) that finds the length of the longest consecutive sequence in O(n). Explain complexity and handle duplicate values and negative integers.` Five supplied behavioral cases evaluate the supported function; they do not prove O(n).

Both exact prompts are reserved for the presentation and were not used in acceptance testing. Select **Live W&B**, quality **0.90**, budget **$0.02**, deadline **45 seconds**, and uncheck **Reuse validated results**. This explicitly bypasses cache even if someone later uses the same prompt.

| Time | Surface and action |
|---|---|
| 0:00–0:25 | **Mission Control.** “Kubernetes schedules compute. Optara schedules AI intelligence.” Explain that a recipe includes model, reasoning, tokens, verification and repair. Set the three constraints. |
| 0:25–1:00 | Run the primary prompt uncached. Follow profile → Top-K candidates → scheduler → W&B inference → evaluator. Read the selected recipe and its actual scheduler reason, including uncertainty. |
| 1:00–1:25 | Inspect **731**, objective quality, full model ID, input/output tokens, precise cost, measured latency, and SLA against the targets. Open **Trace recorded**. Repair is conditional; the preserved historical coding trace demonstrates it if needed. |
| 1:25–2:10 | **marimo/Molab.** “Mission Control shows what Optara decides now. marimo shows the empirical evidence that teaches Optara what to decide next.” Show the LIVE snapshot and overview counts; filter **math** and compare quality/cost/latency and Pareto membership. Expand recorded scheduler decisions. |
| 2:10–3:00 | Open **Shadow comparisons**, then **Policy learning**: production outcomes are immutable and weak evidence cannot promote itself. Open **Benchmark**: equal quality and SLA on this small sample, but Optara cost more. “This validates adaptive control behavior, not universal cost savings.” Finish on the two-surface learning loop. |

Optional follow-up: Run history and Sponsor evidence link the scientific results to real Weave trajectories. Do not start another batch for the demo. A real cache-repeat or manual shadow is available in Mission Control if specifically desired, but is not required for this flow.

The [historical real repair](https://wandb.ai/models-student1155/optara/r/call/01a0987a-6628-797b-bc20-738173ded78f) passed five tests after one repair, at 2.672 seconds and $0.00009673. It predates evaluator v2; present it as historical repair evidence, not current benchmark performance.

If inference access is temporarily unavailable, inspect the [already verified public run](https://wandb.ai/models-student1155/optara/r/call/01a098bc-7d84-7d38-a2f8-6a8276ae7b58) and saved lab evidence. Simulation is explicitly labelled and must never be presented as live W&B execution.
