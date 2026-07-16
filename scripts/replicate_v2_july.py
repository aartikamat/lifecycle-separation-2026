#!/usr/bin/env python3
"""
replicate_v2_july.py

Replication check: does the lifecycle-separation finding hold using
v2 cohort detector on a different time window?

v1 (June 11-25): 20,162 cohort mints x rejection = 4 all-time, 2 window overlap
v2 (June 29 - July 16): 623 cohort mints x July rejection = ?

If v2 overlap is also near-zero, replication is bulletproof.
"""

import json
import os
from datetime import datetime, timezone
from collections import Counter

DATA = "/root/solana-bot/data"
OUT = "/root/solana-bot/analysis"
os.makedirs(OUT, exist_ok=True)

COHORTS_V1 = f"{DATA}/sniper_cohorts_intra.jsonl"
COHORTS_V2 = f"{DATA}/sniper_cohorts_intra_v2.jsonl"
REJECTIONS = f"{DATA}/rejection_outcomes.jsonl"

# v1 window (from paper)
V1_START = datetime(2026, 6, 11, tzinfo=timezone.utc).timestamp()
V1_END = datetime(2026, 6, 26, tzinfo=timezone.utc).timestamp()

# v2 window (from server data)
V2_START = datetime(2026, 6, 29, tzinfo=timezone.utc).timestamp()
V2_END = datetime(2026, 7, 17, tzinfo=timezone.utc).timestamp()


def log(m):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_ts(row):
    for k in ("rejectTs", "sampleTs", "ts", "detected_at"):
        v = row.get(k)
        if isinstance(v, (int, float)) and v > 1_000_000_000:
            return v / 1000 if v > 1e12 else v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except Exception:
                continue
    return None


def load_cohort_mints(path):
    log(f"Loading {path}")
    mints = set()
    tsl = []
    with open(path) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if m:
                    mints.add(m)
                ts = get_ts(r)
                if ts:
                    tsl.append(ts)
            except Exception:
                continue
    ts_min = min(tsl) if tsl else None
    ts_max = max(tsl) if tsl else None
    return mints, ts_min, ts_max


def scan_rejections_windowed(win_start, win_end):
    log(f"Scanning rejections in window "
        f"{datetime.fromtimestamp(win_start, timezone.utc).isoformat()} -> "
        f"{datetime.fromtimestamp(win_end, timezone.utc).isoformat()}")
    all_mints = set()
    window_mints = set()
    dex = Counter()
    rows_total = 0
    rows_window = 0
    with open(REJECTIONS) as f:
        for line in f:
            rows_total += 1
            if rows_total % 200_000 == 0:
                log(f"  {rows_total:,} rows")
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("mint")
            if not m:
                continue
            all_mints.add(m)
            ts = get_ts(r)
            if ts is not None and win_start <= ts <= win_end:
                window_mints.add(m)
                rows_window += 1
                d = r.get("dexId") or r.get("dex")
                if d:
                    dex[d] += 1
    return {
        "all_mints": all_mints,
        "window_mints": window_mints,
        "rows_total": rows_total,
        "rows_window": rows_window,
        "dex": dex,
    }


def main():
    log("=== REPLICATION CHECK: v1 vs v2 lifecycle separation ===")

    v1_mints, v1_ts_min, v1_ts_max = load_cohort_mints(COHORTS_V1)
    v2_mints, v2_ts_min, v2_ts_max = load_cohort_mints(COHORTS_V2)

    log(f"v1: {len(v1_mints):,} mints")
    log(f"v2: {len(v2_mints):,} mints")

    # v2 window from actual data (not hardcoded)
    if v2_ts_min and v2_ts_max:
        v2_win_start = v2_ts_min - 300
        v2_win_end = v2_ts_max + 300
    else:
        v2_win_start = V2_START
        v2_win_end = V2_END

    # Scan rejections for v2 window
    rej_v2 = scan_rejections_windowed(v2_win_start, v2_win_end)

    # v2 x rejection overlap
    v2_overlap_all = v2_mints & rej_v2["all_mints"]
    v2_overlap_window = v2_mints & rej_v2["window_mints"]

    # v1 mints intersection with rejection in v2 window (sanity: cross-window)
    v1_v2_shared = v1_mints & v2_mints

    # Cross-cohort check
    log(f"v1 x v2 cohort mint overlap: {len(v1_v2_shared)}")
    log(f"v2 x rejection (all-time): {len(v2_overlap_all)}")
    log(f"v2 x rejection (v2 window only): {len(v2_overlap_window)}")

    # Report
    out = f"{OUT}/replication_v1_v2_report.txt"
    with open(out, "w") as f:
        f.write("REPLICATION: v1 (June) vs v2 (July) LIFECYCLE-SEPARATION FINDING\n")
        f.write("=" * 65 + "\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n")

        f.write("PIPELINE VERSIONS\n")
        f.write("-" * 65 + "\n")
        f.write("v1: uday-pumpfun-coord-detector (stopped 2026-06-29)\n")
        f.write("v2: uday-pumpfun-coord-detector-v2 (rewrite, currently live)\n\n")

        f.write("v1 COHORT WINDOW (from paper)\n")
        f.write("-" * 65 + "\n")
        f.write(f"Time range: {datetime.fromtimestamp(V1_START, timezone.utc).isoformat()} to "
                f"{datetime.fromtimestamp(V1_END, timezone.utc).isoformat()}\n")
        f.write(f"Unique cohort mints: {len(v1_mints):,}\n\n")

        f.write("v2 COHORT WINDOW\n")
        f.write("-" * 65 + "\n")
        if v2_ts_min:
            f.write(f"Time range: {datetime.fromtimestamp(v2_ts_min, timezone.utc).isoformat()} to "
                    f"{datetime.fromtimestamp(v2_ts_max, timezone.utc).isoformat()}\n")
        f.write(f"Unique cohort mints: {len(v2_mints):,}\n\n")

        f.write("CROSS-COHORT (v1 vs v2) OVERLAP\n")
        f.write("-" * 65 + "\n")
        f.write(f"v1 mints intersect v2 mints: {len(v1_v2_shared)}\n")
        f.write("(Non-overlap between v1 and v2 confirms different populations detected\n"
                "across time windows - important sanity check.)\n\n")

        f.write("v2 COHORT x REJECTION OVERLAP (REPLICATION CHECK)\n")
        f.write("-" * 65 + "\n")
        f.write(f"Rejection rows in v2 window: {rej_v2['rows_window']:,}\n")
        f.write(f"Rejection unique mints in v2 window: {len(rej_v2['window_mints']):,}\n\n")
        f.write(f"v2 cohort x rejection (all-time):     {len(v2_overlap_all):>4} mints "
                f"({len(v2_overlap_all)/max(len(v2_mints),1)*100:.3f}% of v2 cohort)\n")
        f.write(f"v2 cohort x rejection (v2 window):    {len(v2_overlap_window):>4} mints "
                f"({len(v2_overlap_window)/max(len(v2_mints),1)*100:.3f}% of v2 cohort)\n\n")

        f.write("SIDE-BY-SIDE COMPARISON\n")
        f.write("=" * 65 + "\n")
        f.write(f"{'Metric':<40}{'v1 (June)':<15}{'v2 (July)':<15}\n")
        f.write(f"{'Cohort mints':<40}{len(v1_mints):<15,}{len(v2_mints):<15,}\n")
        f.write(f"{'Rejection mints (windowed)':<40}"
                f"{'83':<15}{len(rej_v2['window_mints']):<15,}\n")
        f.write(f"{'Overlap (windowed)':<40}{'2':<15}{len(v2_overlap_window):<15,}\n")
        v1_pct = 2 / 20162 * 100
        v2_pct = len(v2_overlap_window) / max(len(v2_mints), 1) * 100
        f.write(f"{'Overlap % (of cohort)':<40}"
                f"{v1_pct:.3f}%{'':<10}{v2_pct:.3f}%\n\n")

        f.write("DEX DISTRIBUTION (v2 window rejections)\n")
        f.write("-" * 65 + "\n")
        for d, c in rej_v2["dex"].most_common():
            f.write(f"  {d:<20} {c:>10,}\n")

        f.write("\nVERDICT\n")
        f.write("=" * 65 + "\n")
        if len(v2_overlap_window) <= 5 and v2_pct < 1.0:
            f.write("REPLICATION SUCCESS: v2 confirms v1 finding.\n")
            f.write(f"Both windows show <1% cohort-rejection overlap.\n")
            f.write(f"Structural lifecycle-stage separation confirmed across:\n")
            f.write(f"  - Different detection pipeline (v1 vs v2 code)\n")
            f.write(f"  - Different time window (June vs July)\n")
            f.write(f"  - Different cohort population sizes (20,162 vs {len(v2_mints)})\n")
        else:
            f.write("REPLICATION MIXED: v2 shows different pattern than v1.\n")
            f.write(f"v1 overlap: {v1_pct:.3f}%\n")
            f.write(f"v2 overlap: {v2_pct:.3f}%\n")
            f.write("Interpretation needed - could indicate pipeline change effect,\n")
            f.write("regime change, or a real difference worth investigating.\n")

    log(f"Report written: {out}")

    print()
    print("=" * 65)
    print("REPLICATION RESULT (side by side)")
    print("=" * 65)
    print(f"                                v1 (June)       v2 (July)")
    print(f"Cohort mints                    {len(v1_mints):>10,}      {len(v2_mints):>10,}")
    print(f"Rejection mints (windowed)      {'83':>10}      {len(rej_v2['window_mints']):>10,}")
    print(f"Overlap (windowed)              {'2':>10}      {len(v2_overlap_window):>10,}")
    print(f"Overlap %                       {v1_pct:>9.3f}%      {v2_pct:>9.3f}%")
    print(f"v1 x v2 cohort overlap: {len(v1_v2_shared)}")
    print("=" * 65)


if __name__ == "__main__":
    main()
