"""Clean raw CMS files, run documented validation checks, load SQLite, and
export Tableau-ready extracts.

Usage:  python src/build_db.py
Works with either the API pull (src/fetch_cms.py) or CSVs downloaded by hand
from data.cms.gov and saved as data/raw/hospital_info.csv and data/raw/readmissions.csv.
"""
from __future__ import annotations

import sqlite3

import numpy as np
import pandas as pd

from common import DB_PATH, MEASURE_LABELS, PROCESSED, RAW, SQL_DIR, normalize_columns

NUMERIC = [
    "number_of_discharges", "excess_readmission_ratio", "predicted_readmission_rate",
    "expected_readmission_rate", "number_of_readmissions",
]


def to_num(s: pd.Series) -> pd.Series:
    """CMS uses text like 'N/A' and 'Too Few to Report' for suppressed values."""
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def load_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
    info = normalize_columns(pd.read_csv(RAW / "hospital_info.csv", dtype=str))
    readm = normalize_columns(pd.read_csv(RAW / "readmissions.csv", dtype=str))
    for df in (info, readm):
        df["facility_id"] = df["facility_id"].str.strip().str.zfill(6)
        df["state"] = df["state"].str.strip().str.upper()
    for c in NUMERIC:
        readm[c + "_raw"] = readm[c]
        readm[c] = to_num(readm[c])
    info["hospital_overall_rating"] = to_num(info["hospital_overall_rating"])
    readm["measure_label"] = readm["measure_name"].map(MEASURE_LABELS)
    return info, readm


class Checks:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, name: str, passed: bool, detail: str) -> None:
        self.rows.append((name, "PASS" if passed else "WARN", detail))

    def to_markdown(self) -> str:
        lines = ["# Data quality report", "", "| Check | Result | Detail |", "|---|---|---|"]
        lines += [f"| {n} | {r} | {d} |" for n, r, d in self.rows]
        return "\n".join(lines) + "\n"


def validate(info: pd.DataFrame, readm: pd.DataFrame) -> Checks:
    c = Checks()
    dup = info["facility_id"].duplicated().sum()
    c.add("Unique facility IDs (hospital info)", dup == 0, f"{dup} duplicate IDs")

    dup_rm = readm.duplicated(["facility_id", "measure_name"]).sum()
    c.add("One row per hospital x measure", dup_rm == 0, f"{dup_rm} duplicate rows")

    unknown = sorted(set(readm["measure_name"]) - set(MEASURE_LABELS))
    c.add("Known HRRP measures only", not unknown, f"unexpected: {unknown or 'none'}")

    orphan = (~readm["facility_id"].isin(info["facility_id"])).sum()
    c.add("Readmission rows join to a hospital", orphan == 0, f"{orphan} rows without a match")

    ok = readm.dropna(subset=["excess_readmission_ratio", "predicted_readmission_rate",
                              "expected_readmission_rate"])
    recomputed = ok["predicted_readmission_rate"] / ok["expected_readmission_rate"]
    off = (recomputed - ok["excess_readmission_ratio"]).abs().gt(0.002).sum()
    c.add("ERR = predicted / expected (tol 0.002)", off == 0, f"{off} of {len(ok):,} rows off")

    err = readm["excess_readmission_ratio"].dropna()
    out = (~err.between(0.5, 2.0)).sum()
    c.add("ERR in plausible range 0.5-2.0", out == 0, f"{out} rows outside range")

    supp = readm["number_of_readmissions"].isna().mean()
    c.add("Suppressed readmission counts", True,
          f"{supp:.1%} of rows suppressed ('Too Few to Report' / N/A); kept, excluded from O/E stats")

    periods = readm[["start_date", "end_date"]].drop_duplicates()
    c.add("Single reporting period", len(periods) == 1,
          "; ".join(f"{a} to {b}" for a, b in periods.itertuples(index=False)))
    return c


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    info, readm = load_raw()
    checks = validate(info, readm)
    (PROCESSED / "data_quality_report.md").write_text(checks.to_markdown())
    print(checks.to_markdown())

    keep_info = ["facility_id", "facility_name", "address", "city", "state", "zip", "county",
                 "hospital_type", "hospital_ownership", "emergency_services",
                 "hospital_overall_rating"]
    info = info[[c for c in keep_info if c in info.columns]]
    keep_rm = ["facility_id", "state", "measure_name", "measure_label", "start_date", "end_date",
               "footnote"] + NUMERIC
    readm = readm[[c for c in keep_rm if c in readm.columns]]

    DB_PATH.unlink(missing_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        info.to_sql("hospital", con, index=False)
        readm.to_sql("readmission", con, index=False)
        for f in sorted(SQL_DIR.glob("*.sql")):
            con.executescript(f.read_text())
        for view, fname in [
            ("v_wa_hospital_measures", "wa_hospital_measures.csv"),
            ("v_state_measure_summary", "state_measure_summary.csv"),
            ("v_wa_hrrp_coverage", "wa_hrrp_coverage.csv"),
        ]:
            df = pd.read_sql(f"SELECT * FROM {view}", con)
            df.to_csv(PROCESSED / fname, index=False)
            print(f"wrote {fname}: {len(df):,} rows")


if __name__ == "__main__":
    main()
