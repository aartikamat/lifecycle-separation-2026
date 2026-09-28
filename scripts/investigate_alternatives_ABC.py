#!/usr/bin/env python3
"""
investigate_alternatives_ABC.py

Rules out 3 alternative explanations for the cohort-rejection disjoint finding:
  A. Data source mismatch  (what data feeds each pipeline)
  B. Time window artifact  (do they overlap in the 14-day cohort window?)
  C. DEX venue asymmetry   (different DEXes = different token universes)

Output: analysis/alternatives_ABC_report.txt
"""

import json
import os
import subprocess
from datetime import datetime, timezone
from collections import Counter

DATA = "data"
OUT = "analysis"
os.makedirs(OUT, exist_ok=True)

COHORTS = f"{DATA}/sniper_cohorts_intra.jsonl"
REJECTIONS = f"{DATA}/rejection_outcomes.jsonl"

COHORT_WINDOW_START = datetime(2026, 6, 11, tzinfo=timezone.utc).timestamp()
COHORT_WINDOW_END = datetime(2026, 6, 26, tzinfo=timezone.utc).timestamp()


def log(m):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def sample_schemas():
    """A: Peek at first row of each file to identify data source."""
    log("A: Sampling schemas from both files")
    def peek(path, n=3):
        rows = []
        with open(path) as f:
            for i, line in enumerate(f):
                if i >= n:
                    break
                try:
                    rows.append(json.loads(line))
                except:
                    continue
        return rows

    cohort_sample = peek(COHORTS, 2)
    reject_sample = peek(REJECTIONS, 2)

    cohort_fields = set()
    for r in cohort_sample:
        cohort_fields.update(r.keys())
    reject_fields = set()
    for r in reject_sample:
        reject_fields.update(r.keys())

    return {
        "cohort_first_row": cohort_sample[0] if cohort_sample else {},
        "reject_first_row": reject_sample[0] if reject_sample else {},
        "cohort_fields": sorted(cohort_fields),
        "reject_fields": sorted(reject_fields),
    }


def get_ts(row):
    """Try common timestamp fields, return epoch seconds or None."""
    for k in ("rejectTs", "sampleTs", "ts", "timestamp", "detected_at",
              "blockTime", "createdAt", "created_at"):
        v = row.get(k)
        if isinstance(v, (int, float)) and v > 1_000_000_000:
            return v / 1000 if v > 1e12 else v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except:
                continue
    return None


def load_cohort_mints_and_dex():
    """Load cohort mints + dexId distribution."""
    log("Loading cohort mints + DEX")
    mints = set()
    dex_counts = Counter()
    ts_list = []
    with open(COHORTS) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if m:
                    mints.add(m)
                dex = r.get("dexId") or r.get("dex") or r.get("venue")
                if dex:
                    dex_counts[dex] += 1
                ts = get_ts(r)
                if ts:
                    ts_list.append(ts)
            except:
                continue
    return mints, dex_counts, ts_list


def scan_rejections_windowed(cohort_mints):
    """B + C: within cohort window, check overlap and DEX distribution."""
    log("B+C: Scanning rejections with time-window filter")
    reject_mints_in_window = set()
    reject_dex_in_window = Counter()
    all_reject_mints = set()
    all_reject_dex = Counter()
    ts_min = None
    ts_max = None
    rows_in_window = 0
    rows_total = 0
    ts_missing = 0

    with open(REJECTIONS) as f:
        for line in f:
            rows_total += 1
            if rows_total % 200_000 == 0:
                log(f"  {rows_total:,} rows scanned")
            try:
                r = json.loads(line)
            except:
                continue
            m = r.get("mint")
            if not m:
                continue
            all_reject_mints.add(m)
            dex = r.get("dexId") or r.get("dex")
            if dex:
                all_reject_dex[dex] += 1

            ts = get_ts(r)
            if ts is None:
                ts_missing += 1
                continue
            ts_min = ts if ts_min is None else min(ts_min, ts)
            ts_max = ts if ts_max is None else max(ts_max, ts)

            if COHORT_WINDOW_START <= ts <= COHORT_WINDOW_END:
                rows_in_window += 1
                reject_mints_in_window.add(m)
                if dex:
                    reject_dex_in_window[dex] += 1

    return {
        "all_reject_mints": all_reject_mints,
        "all_reject_dex": all_reject_dex,
        "reject_mints_in_window": reject_mints_in_window,
        "reject_dex_in_window": reject_dex_in_window,
        "rows_total": rows_total,
        "rows_in_window": rows_in_window,
        "ts_missing": ts_missing,
        "ts_min": ts_min,
        "ts_max": ts_max,
    }


def main():
    log("Starting alternatives A/B/C investigation")

    # Schemas
    schemas = sample_schemas()

    # Cohort load
    cohort_mints, cohort_dex, cohort_ts = load_cohort_mints_and_dex()
    log(f"Cohort: {len(cohort_mints):,} mints, "
        f"{len(cohort_dex)} DEX categories, {len(cohort_ts)} timestamped rows")

    # Rejection scan
    rej = scan_rejections_windowed(cohort_mints)
    log(f"Rejection: {rej['rows_total']:,} total rows, "
        f"{len(rej['all_reject_mints']):,} unique mints, "
        f"{rej['rows_in_window']:,} rows in cohort window")

    # Overlap analysis (windowed)
    overlap_all = cohort_mints & rej["all_reject_mints"]
    overlap_window = cohort_mints & rej["reject_mints_in_window"]

    # Time windows
    reject_ts_min = datetime.fromtimestamp(rej["ts_min"], timezone.utc).isoformat() if rej["ts_min"] else "?"
    reject_ts_max = datetime.fromtimestamp(rej["ts_max"], timezone.utc).isoformat() if rej["ts_max"] else "?"
    cohort_ts_min = datetime.fromtimestamp(min(cohort_ts), timezone.utc).isoformat() if cohort_ts else "?"
    cohort_ts_max = datetime.fromtimestamp(max(cohort_ts), timezone.utc).isoformat() if cohort_ts else "?"

    # Write report
    out = f"{OUT}/alternatives_ABC_report.txt"
    with open(out, "w") as f:
        f.write("ALTERNATIVES A/B/C — RULING OUT ARTIFACTS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")

        f.write("A. DATA SOURCE SCHEMAS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Cohort fields: {schemas['cohort_fields']}\n\n")
        f.write(f"Cohort first row (redacted keys):\n")
        for k, v in schemas["cohort_first_row"].items():
            f.write(f"  {k}: {str(v)[:120]}\n")
        f.write(f"\nRejection fields: {schemas['reject_fields']}\n\n")
        f.write(f"Rejection first row (redacted keys):\n")
        for k, v in schemas["reject_first_row"].items():
            f.write(f"  {k}: {str(v)[:120]}\n")

        f.write("\n\nB. TIME WINDOW OVERLAP\n")
        f.write("-" * 60 + "\n")
        f.write(f"Cohort window:    {cohort_ts_min}  →  {cohort_ts_max}\n")
        f.write(f"Rejection window: {reject_ts_min}  →  {reject_ts_max}\n")
        f.write(f"Rejection rows total: {rej['rows_total']:,}\n")
        f.write(f"Rejection rows within cohort window: {rej['rows_in_window']:,}\n")
        f.write(f"Rows with missing timestamp: {rej['ts_missing']:,}\n")
        f.write(f"Rejection unique mints (all time): {len(rej['all_reject_mints']):,}\n")
        f.write(f"Rejection unique mints (cohort window): {len(rej['reject_mints_in_window']):,}\n")
        f.write(f"\nCohort × rejection overlap (all time):    {len(overlap_all):,} mints\n")
        f.write(f"Cohort × rejection overlap (window only): {len(overlap_window):,} mints\n")

        f.write("\n\nC. DEX VENUE ASYMMETRY\n")
        f.write("-" * 60 + "\n")
        f.write("Cohort DEX distribution:\n")
        for dex, cnt in cohort_dex.most_common():
            f.write(f"  {dex:<20} {cnt:>10,}\n")
        f.write("\nRejection DEX distribution (all time):\n")
        for dex, cnt in rej["all_reject_dex"].most_common():
            f.write(f"  {dex:<20} {cnt:>10,}\n")
        f.write("\nRejection DEX distribution (cohort window):\n")
        for dex, cnt in rej["reject_dex_in_window"].most_common():
            f.write(f"  {dex:<20} {cnt:>10,}\n")

        f.write("\n\nCONCLUSION\n")
        f.write("=" * 60 + "\n")
        if len(overlap_window) < 10 and rej["rows_in_window"] > 1000:
            f.write("Time window is NOT the explanation.\n")
            f.write(f"Within the overlapping 14-day window, "
                    f"{rej['rows_in_window']:,} rejection rows exist but only "
                    f"{len(overlap_window):,} overlap with cohort mints.\n")
        elif rej["rows_in_window"] < 1000:
            f.write("Time window MAY be the explanation.\n")
            f.write(f"Only {rej['rows_in_window']:,} rejection rows within cohort window.\n")

        cohort_dex_set = set(cohort_dex.keys())
        reject_dex_set = set(rej["all_reject_dex"].keys())
        if cohort_dex_set and reject_dex_set and not (cohort_dex_set & reject_dex_set):
            f.write("\nDEX venue mismatch IS complete: no shared DEX between cohort and rejection.\n")
        elif cohort_dex_set and reject_dex_set:
            shared = cohort_dex_set & reject_dex_set
            f.write(f"\nShared DEX venues: {shared}\n")

    log(f"Report: {out}")
    print()
    print("=" * 60)
    print("HEADLINE")
    print("=" * 60)
    print(f"Cohort window:    {cohort_ts_min[:19]} → {cohort_ts_max[:19]}")
    print(f"Rejection window: {reject_ts_min[:19]} → {reject_ts_max[:19]}")
    print(f"Rejection rows in cohort's 14-day window: {rej['rows_in_window']:,}")
    print(f"Cohort × rejection overlap (all time):    {len(overlap_all)}")
    print(f"Cohort × rejection overlap (window only): {len(overlap_window)}")
    print(f"Cohort DEX: {dict(cohort_dex.most_common(5))}")
    print(f"Reject DEX: {dict(rej['all_reject_dex'].most_common(5))}")


if __name__ == "__main__":
    main()
