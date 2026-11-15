"""Shared helpers: paths, dataset registry, and column normalization."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
DB_PATH = ROOT / "data" / "hospital_quality.db"
SQL_DIR = ROOT / "sql"

# CMS Provider Data Catalog dataset IDs (https://data.cms.gov/provider-data/)
DATASETS = {
    "hospital_info": "xubh-q36u",      # Hospital General Information
    "readmissions": "9n3s-kdb3",       # Hospital Readmissions Reduction Program (HRRP)
}

# The CSV download uses "City/Town"; the API returns "citytown". Map both to one name.
ALIASES = {
    "citytown": "city", "city_town": "city",
    "countyparish": "county", "county_parish": "county",
    "zip_code": "zip",
}

MEASURE_LABELS = {
    "READM-30-AMI-HRRP": "Heart attack (AMI)",
    "READM-30-HF-HRRP": "Heart failure",
    "READM-30-PN-HRRP": "Pneumonia",
    "READM-30-COPD-HRRP": "COPD",
    "READM-30-CABG-HRRP": "Bypass surgery (CABG)",
    "READM-30-HIP-KNEE-HRRP": "Hip/knee replacement",
}


def snake(name: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name)).strip("_").lower()
    return ALIASES.get(s, s)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [snake(c) for c in out.columns]
    return out
