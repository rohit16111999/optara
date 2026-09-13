# Optara on marimo / Molab

**Judge link:** [Optara Experiment & Intelligence Lab](https://molab.marimo.io/github/rohit16111999/optara/blob/main/experiment_lab/optara_lab.py).

This is a public GitHub-synced Molab preview, not a claim of a permanently running authenticated cloud kernel. The committed `experiment_lab/__marimo__/session/optara_lab.py.json` provides rendered outputs. The notebook and safe evidence remain reproducible from GitHub. Molab's [official sharing documentation](https://docs.marimo.io/guides/molab/#mirror-notebooks-from-github) describes this preview and server distinction.

**One-step interactive launch:** open the judge link and choose **Run it now → Run on server**; sign in to Molab if prompted. The notebook loads public-safe evidence automatically and requires no W&B key. A running notebook's **Share → Run as app** option provides its app-view link. A dedicated authenticated app session is not claimed until verified.

For a local interactive presentation:

```powershell
.\lab.ps1
```

Equivalent explicit command:

```powershell
.venv\Scripts\python.exe -m marimo run experiment_lab/optara_lab.py --host 127.0.0.1 --port 2718 --headless --no-sandbox
```

Open http://127.0.0.1:2718. Inline dependencies support a fresh Molab environment. No private prompts, outputs, credentials, or local API are needed to explore saved evidence. A cloud kernel downloads the same `data/evidence.json` from GitHub. The upload control also accepts that file directly.

Choose **Saved demo evidence** for the committed LIVE snapshot, or **Local API** for current local records. Namespace and family selectors apply to evidence exploration. A mismatched simulation/live upload is rejected rather than relabelled. Benchmark scope remains the full fixed suite and latest completed report; historical report versions are listed separately.

The lab exposes overview counts, quality/cost/latency charts, family Pareto membership, actual scheduler decisions, shadow deltas, explicit policy gates/confidence, benchmark metrics, run history and sponsor evidence. Nothing on page load starts paid inference. The separate controlled-experiment form defaults to Simulation, requires explicit submission, and targets only the local backend. Do not use it for the judge walkthrough.

To refresh the safe snapshot and rendered preview intentionally:

```powershell
.venv\Scripts\python.exe -m scripts.export_evidence --mode live --output data/evidence.json
.venv\Scripts\python.exe -m marimo export session experiment_lab/optara_lab.py --no-sandbox --force-overwrite
```

Inspect and secret-scan regenerated evidence before publishing it. The current committed export contains synthetic benchmark/demo metadata and excludes prompt/output fields. Exported scheduler metrics and candidate reasons remain measured evidence; none are invented to improve the presentation.
