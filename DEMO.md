# Optara v1 — saved-run demo

60–90 seconds. Start locally with `.\start.ps1 -Production` after building the frontend. Use the existing local database; a fresh clone includes the notebook evidence snapshot, not saved private runtime records. Do not click Run Optara or start experiments.

1. Open **Runs** in **Live W&B**. Find `9dbae5a2` (the exact arithmetic task) and click its **Inspect run** arrow. This only loads saved data.
2. On **Execute**, show **Selected Execution**: Focused v2, `openai/gpt-oss-20b`, low reasoning, 384-token allowance, verifier off and one-repair limit. Show actual quality 1.00, $0.00000584, 0.563s, 128 tokens and SLA HIT.
3. Scroll to **Why This Execution?** and show the selected candidate, expected metrics, stored rejection reasons and scheduler explanation.
4. Show **Model Result** (703), objective exact-match evaluation, zero repairs, cache MISS and **Execution Evidence**. Use **VERIFY IN WEAVE** for the stored trace if account access permits.
5. Open **Evaluations**. Show both Pareto charts, recipe performance and the honest benchmark result. Finish on **OPEN REPRODUCIBLE EVALUATION NOTEBOOK**; leave Advanced Experiments collapsed.

[Companion notebook](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py) · [Saved trace](https://wandb.ai/models-student1155/optara/r/call/01a098ad-631e-76a8-af46-c4f5b4f347e3)

The public deployment retains the earlier UI; record this release locally. No new inference, calibration, benchmark or shadow execution is needed.
