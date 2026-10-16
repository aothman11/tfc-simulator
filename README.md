# TFC Practice Simulator

> **Practice model – not the real game. All numbers are estimates.**

## Quick start

```bash
pip install -r requirements.txt
python -m tfc run scenarios/01_hold_r2.yaml          # run one scenario
python -m tfc calibrate                               # check model vs R2 actuals
python -m tfc montecarlo scenarios/inflate_pet.yaml  # GO/NO-GO verdict (500 runs)
python -m tfc scenarios                               # compare all pre-built scenarios
streamlit run tfc/ui/app.py                           # interactive web UI
pytest                                                # run test suite
```

## Folder layout

```
data/           YAML data files (products, customers, suppliers, operations, round2/3 baselines)
assumptions.yaml  every value NOT from real game data, with min/max for MC
scenarios/      pre-built YAML scenario files (01–16 + inflate_pet)
tfc/engine/     pure-Python simulation engine (no UI code)
tfc/ui/         Streamlit web interface
tests/          pytest test suite
```

## Key rules

- This model **cannot** reproduce the real game's engine output exactly.
- Every assumption that is not from your real game data is in `assumptions.yaml` and marked UNVERIFIED.
- Monte Carlo samples UNVERIFIED assumptions uniformly across their min/max range.
- Results are deterministic given the same `seed`.
