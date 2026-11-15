"""Pull hospital quality datasets from the CMS Provider Data Catalog API.

Paginates through the DKAN datastore API, writes each dataset to data/raw/,
and logs row counts so every refresh is traceable.

Usage:  python src/fetch_cms.py
"""
from __future__ import annotations

import datetime as dt
import json
import time

import pandas as pd
import requests

from common import DATASETS, RAW, normalize_columns

BASE = "https://data.cms.gov/provider-data/api/1/datastore/query/{id}/0"
PAGE = 1500  # CMS caps page size; 1500 is safely under the limit


def fetch_dataset(dataset_id: str, session: requests.Session) -> pd.DataFrame:
    rows, offset, total = [], 0, None
    while total is None or offset < total:
        resp = session.get(
            BASE.format(id=dataset_id),
            params={"limit": PAGE, "offset": offset, "count": "true", "results": "true"},
            timeout=60,
        )
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("results", [])
        total = int(payload.get("count", len(batch)))
        if not batch:
            break
        rows.extend(batch)
        offset += len(batch)
        print(f"  {dataset_id}: {offset:,}/{total:,} rows")
        time.sleep(0.2)  # be polite to the API
    if len(rows) != total:
        raise RuntimeError(f"{dataset_id}: expected {total} rows, got {len(rows)}")
    return normalize_columns(pd.DataFrame(rows))


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    log = {"pulled_at": dt.datetime.now().isoformat(timespec="seconds"), "datasets": {}}
    with requests.Session() as s:
        s.headers["User-Agent"] = "wa-hospital-readmissions portfolio project"
        for name, ds_id in DATASETS.items():
            print(f"Fetching {name} ({ds_id})")
            df = fetch_dataset(ds_id, s)
            df.to_csv(RAW / f"{name}.csv", index=False)
            log["datasets"][name] = {"id": ds_id, "rows": len(df), "columns": list(df.columns)}
    (RAW / "fetch_log.json").write_text(json.dumps(log, indent=2))
    print("Done. Raw files in data/raw/")


if __name__ == "__main__":
    main()
