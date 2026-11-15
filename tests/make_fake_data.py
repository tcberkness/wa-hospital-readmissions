"""Generate small synthetic CMS-shaped files so the pipeline can be tested offline.
Column names mirror the CMS CSV downloads. Values are random, not real hospitals."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from common import MEASURE_LABELS, RAW  # noqa: E402

rng = np.random.default_rng(7)
states = ["WA"] * 90 + list(rng.choice(["CA", "OR", "TX", "NY", "ID", "FL"], 600))
ids = [f"{i:06d}" for i in range(10001, 10001 + len(states))]
types = rng.choice(["Acute Care Hospitals", "Critical Access Hospitals"], len(states), p=[0.7, 0.3])
info = pd.DataFrame({
    "Facility ID": ids, "Facility Name": [f"Test Hospital {i}" for i in range(len(ids))],
    "Address": "1 Main St", "City/Town": "TESTVILLE", "State": states, "ZIP Code": "98000",
    "County/Parish": "KING", "Hospital Type": types, "Hospital Ownership": "Voluntary non-profit - Private",
    "Emergency Services": "Yes",
    "Hospital overall rating": [str(x) if x else "Not Available" for x in rng.integers(0, 6, len(ids))],
})
rows = []
for fid, st, t in zip(ids, states, types):
    if t == "Critical Access Hospitals":
        continue  # CAHs are not in HRRP
    shift = -0.02 if st == "WA" else 0.0
    for m in MEASURE_LABELS:
        n = int(rng.integers(20, 900))
        exp = rng.uniform(8, 20)
        err = float(np.clip(rng.normal(1 + shift, 0.05), 0.7, 1.4))
        pred = exp * err
        obs = rng.poisson(pred / 100 * n)
        small = n < 60
        rows.append({
            "Facility Name": "x", "Facility ID": fid, "State": st, "Measure Name": m,
            "Number of Discharges": "N/A" if small else str(n), "Footnote": "",
            "Excess Readmission Ratio": "N/A" if small else f"{err:.4f}",
            "Predicted Readmission Rate": "N/A" if small else f"{pred:.4f}",
            "Expected Readmission Rate": "N/A" if small else f"{exp:.4f}",
            "Number of Readmissions": "Too Few to Report" if small or obs < 11 else str(obs),
            "Start Date": "07/01/2021", "End Date": "06/30/2024",
        })
RAW.mkdir(parents=True, exist_ok=True)
info.to_csv(RAW / "hospital_info.csv", index=False)
pd.DataFrame(rows).to_csv(RAW / "readmissions.csv", index=False)
print("Synthetic files written to data/raw/")
