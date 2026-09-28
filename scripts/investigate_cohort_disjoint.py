#!/usr/bin/env python3
"""
investigate_cohort_disjoint.py

Question: 20,162 cohort mints exist, but only 571 appear in rejection stream.
Where are the other 19,591?

Bulletproof-paper prerequisite: rule out every alternative explanation
before claiming disjoint populations.

Alternative hypotheses to test:
  H1: Cohort mints GRADUATED (never rejected)
  H2: Cohort mints appear in graveyard as dead (rejected offstage)
  H3: Cohort mints and rejection stream cover different TIME windows
  H4: Cohort mints are on different DEX venues
  H5: Cohort mints are in older data (before rejection tracker started)

Outputs to analysis/cohort_disjoint_investigation.txt
"""

import json
import os
from collections import Counter, defaultdict
from datetime import datetime

DATA = "data"
OUT = "analysis"
os.makedirs(OUT, exist_ok=True)

COHORTS = f"{DATA}/sniper_cohorts_intra.jsonl"
REJECTIONS = f"{DATA}/rejection_outcomes.jsonl"
STATUS = f"{DATA}/pumpfun_status_transitions.jsonl"
GRAVEYARD = f"{DATA}/graveyard_lifecycle.jsonl"


def log(m):
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {m}", flush=True)


def load_cohort_mints():
    log(f"Loading cohort mints")
    mints = set()
    cohort_ts_range = []
    with open(COHORTS) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if m:
                    mints.add(m)
                ts = r.get("detected_at") or r.get("ts") or r.get("timestamp")
                if ts:
                    cohort_ts_range.append(ts)
            except:
                continue
    return mints, cohort_ts_range


def check_h1_graduated(cohort_mints):
    """H1: How many cohort mints graduated?"""
    log("H1: Checking graduations")
    graduated = set()
    zombie = set()
    drained = set()
    alive = set()
    if not os.path.exists(STATUS):
        log(f"  {STATUS} not found - skipping H1")
        return {"graduated": 0, "zombie": 0, "drained": 0, "alive_bonding": 0,
                "file_missing": True}

    with open(STATUS) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if not m or m not in cohort_mints:
                    continue
                state = r.get("state") or r.get("event") or r.get("status", "")
                s = str(state).upper()
                if "GRADUATED" in s:
                    graduated.add(m)
                elif "ZOMBIE" in s:
                    zombie.add(m)
                elif "DRAINED" in s:
                    drained.add(m)
                elif "ALIVE_BONDING" in s or "ALIVE" in s:
                    alive.add(m)
            except:
                continue

    return {
        "graduated": len(graduated),
        "zombie": len(zombie),
        "drained": len(drained),
        "alive_bonding": len(alive),
        "any_status": len(graduated | zombie | drained | alive),
    }


def check_h2_graveyard(cohort_mints):
    """H2: How many cohort mints are in graveyard?"""
    log("H2: Checking graveyard")
    if not os.path.exists(GRAVEYARD):
        return {"file_missing": True}
    in_graveyard = set()
    states = Counter()
    with open(GRAVEYARD) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if not m or m not in cohort_mints:
                    continue
                in_graveyard.add(m)
                st = r.get("state") or r.get("event") or ""
                states[str(st)] += 1
            except:
                continue
    return {
        "unique_mints_in_graveyard": len(in_graveyard),
        "state_counts": dict(states.most_common(10)),
    }


def check_h3_time_windows(cohort_ts_range):
    """H3: When was cohort data collected vs rejection data?"""
    log("H3: Checking time windows")
    if not cohort_ts_range:
        return {"cohort_ts_missing": True}

    # Parse cohort timestamps (may be epoch ms or ISO)
    cohort_epochs = []
    for ts in cohort_ts_range:
        try:
            if isinstance(ts, (int, float)):
                epoch = float(ts)
                if epoch > 1e12:
                    epoch = epoch / 1000
                cohort_epochs.append(epoch)
            elif isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                cohort_epochs.append(dt.timestamp())
        except:
            continue

    if not cohort_epochs:
        return {"cohort_ts_parse_failed": True}

    cohort_min = datetime.utcfromtimestamp(min(cohort_epochs))
    cohort_max = datetime.utcfromtimestamp(max(cohort_epochs))

    # Rejection stream timestamps - sample first 1000 and last 1000
    log("  Sampling rejection timestamps")
    reject_ts_early = []
    reject_ts_late = []
    with open(REJECTIONS) as f:
        for i, line in enumerate(f):
            if i > 1000:
                break
            try:
                r = json.loads(line)
                ts = r.get("rejectTs") or r.get("sampleTs") or r.get("ts")
                if ts:
                    if isinstance(ts, (int, float)):
                        e = ts / 1000 if ts > 1e12 else ts
                        reject_ts_early.append(e)
            except:
                continue

    # Get file end via tail
    import subprocess
    tail = subprocess.check_output(["tail", "-1000", REJECTIONS]).decode()
    for line in tail.split("\n"):
        try:
            r = json.loads(line)
            ts = r.get("rejectTs") or r.get("sampleTs") or r.get("ts")
            if ts:
                if isinstance(ts, (int, float)):
                    e = ts / 1000 if ts > 1e12 else ts
                    reject_ts_late.append(e)
        except:
            continue

    reject_min = datetime.utcfromtimestamp(min(reject_ts_early)) if reject_ts_early else None
    reject_max = datetime.utcfromtimestamp(max(reject_ts_late)) if reject_ts_late else None

    return {
        "cohort_window_start": cohort_min.isoformat(),
        "cohort_window_end": cohort_max.isoformat(),
        "reject_window_start": reject_min.isoformat() if reject_min else "?",
        "reject_window_end": reject_max.isoformat() if reject_max else "?",
    }


def check_h4_dex(cohort_mints):
    """H4: What DEX are cohort mints trading on (from what data we have)?"""
    log("H4: Checking DEX venues in cohort data")
    dex_counts = Counter()
    with open(COHORTS) as f:
        for line in f:
            try:
                r = json.loads(line)
                m = r.get("mint")
                if m in cohort_mints:
                    dex = r.get("dexId") or r.get("dex") or r.get("venue") or "unknown"
                    dex_counts[dex] += 1
            except:
                continue
    return dict(dex_counts.most_common(10))


def check_h5_overlap(cohort_mints):
    """H5: What fraction of cohort mints appear in rejection stream?"""
    log("H5: Computing set overlap")
    reject_mints = set()
    with open(REJECTIONS) as f:
        for i, line in enumerate(f):
            if i % 100_000 == 0:
                log(f"  {i:,} rejection rows scanned")
            try:
                r = json.loads(line)
                m = r.get("mint")
                if m:
                    reject_mints.add(m)
            except:
                continue

    overlap = cohort_mints & reject_mints
    only_cohort = cohort_mints - reject_mints
    only_reject = reject_mints - cohort_mints

    return {
        "cohort_total": len(cohort_mints),
        "reject_total": len(reject_mints),
        "overlap": len(overlap),
        "only_in_cohort": len(only_cohort),
        "only_in_rejection": len(only_reject),
        "cohort_overlap_pct": len(overlap) / len(cohort_mints) * 100 if cohort_mints else 0,
    }


def main():
    cohort_mints, cohort_ts = load_cohort_mints()
    log(f"Cohort mints: {len(cohort_mints):,}")

    r_h1 = check_h1_graduated(cohort_mints)
    r_h2 = check_h2_graveyard(cohort_mints)
    r_h3 = check_h3_time_windows(cohort_ts)
    r_h4 = check_h4_dex(cohort_mints)
    r_h5 = check_h5_overlap(cohort_mints)

    out_path = f"{OUT}/cohort_disjoint_investigation.txt"
    with open(out_path, "w") as f:
        f.write("COHORT DISJOINT-POPULATION INVESTIGATION\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n\n")

        f.write("QUESTION: 20,162 cohort mints, only 571 in rejection stream.\n")
        f.write("Where are the other 19,591?\n\n")

        f.write("H1: GRADUATED (never rejected)\n")
        f.write("-" * 60 + "\n")
        for k, v in r_h1.items():
            f.write(f"  {k}: {v}\n")

        f.write("\nH2: IN GRAVEYARD (dead offstage)\n")
        f.write("-" * 60 + "\n")
        for k, v in r_h2.items():
            f.write(f"  {k}: {v}\n")

        f.write("\nH3: TIME WINDOW OVERLAP\n")
        f.write("-" * 60 + "\n")
        for k, v in r_h3.items():
            f.write(f"  {k}: {v}\n")

        f.write("\nH4: DEX VENUES IN COHORT DATA\n")
        f.write("-" * 60 + "\n")
        for k, v in r_h4.items():
            f.write(f"  {k}: {v:,}\n")

        f.write("\nH5: SET OVERLAP (definitive)\n")
        f.write("-" * 60 + "\n")
        for k, v in r_h5.items():
            f.write(f"  {k}: {v}\n")

        f.write("\nCONCLUSION\n")
        f.write("=" * 60 + "\n")
        graduated_pct = (r_h1.get('graduated', 0) / len(cohort_mints) * 100) if cohort_mints else 0
        graveyard_pct = (r_h2.get('unique_mints_in_graveyard', 0) / len(cohort_mints) * 100) if cohort_mints else 0
        f.write(f"Of {len(cohort_mints):,} cohort mints:\n")
        f.write(f"  {r_h5.get('overlap', 0):,} appear in rejection stream ({r_h5.get('cohort_overlap_pct', 0):.1f}%)\n")
        f.write(f"  {r_h1.get('graduated', 0):,} graduated ({graduated_pct:.1f}%)\n")
        f.write(f"  {r_h2.get('unique_mints_in_graveyard', 0):,} in graveyard ({graveyard_pct:.1f}%)\n")
        f.write(f"  Time windows: cohort {r_h3.get('cohort_window_start', '?')} to {r_h3.get('cohort_window_end', '?')}\n")
        f.write(f"                rejects {r_h3.get('reject_window_start', '?')} to {r_h3.get('reject_window_end', '?')}\n")

    log(f"Report: {out_path}")
    print()
    print("=" * 60)
    print("KEY NUMBERS")
    print("=" * 60)
    for k, v in r_h5.items():
        print(f"  {k}: {v}")
    print(f"\nGraduated:  {r_h1.get('graduated', 0):,}")
    print(f"Graveyard:  {r_h2.get('unique_mints_in_graveyard', 0):,}")
    print(f"Cohort window: {r_h3.get('cohort_window_start', '?')} → {r_h3.get('cohort_window_end', '?')}")
    print(f"Reject window: {r_h3.get('reject_window_start', '?')} → {r_h3.get('reject_window_end', '?')}")


if __name__ == "__main__":
    main()
