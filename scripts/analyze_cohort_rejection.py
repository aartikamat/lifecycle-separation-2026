#!/usr/bin/env python3
"""
analyze_cohort_rejection.py

Joins sniper cohorts against rejection outcomes to answer:
  "Do rejects on tokens caught by sniper cohorts 10x more often
   than rejects on cohortless tokens?"

Novel cross-dataset finding for future paper.

INPUTS:
  /root/solana-bot/data/sniper_cohorts_intra.jsonl  (~20K rows, ~14MB)
  /root/solana-bot/data/rejection_outcomes.jsonl    (~712K rows, ~433MB - STREAMED)

OUTPUTS:
  /root/solana-bot/analysis/cohort_rejection_join_report.txt   (human readable)
  /root/solana-bot/analysis/cohort_rejection_join_by_mint.csv  (mint-level detail)
  /root/solana-bot/analysis/cohort_rejection_summary.csv       (aggregate stats)

DESIGN NOTES:
- Uses readline streaming for the 433MB rejection_outcomes file
  (per memory rule: never readFileSync large JSONL - OOM risk)
- Cohort file is small enough to fit in RAM as a set of mints
- Runs in ~5-10 minutes on the current droplet
- Zero PM2 process needed (one-shot analysis)

Author: Arati Uday Kamat
Date: 2026-07-16
"""

import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime

COHORTS_FILE = "/root/solana-bot/data/sniper_cohorts_intra.jsonl"
REJECTIONS_FILE = "/root/solana-bot/data/rejection_outcomes.jsonl"
OUTPUT_DIR = "/root/solana-bot/analysis"

os.makedirs(OUTPUT_DIR, exist_ok=True)

WINNER_MULTIPLE = 10.0  # define "counterfactual winner" as >=10x max price move


def log(msg):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_cohort_mints():
    """Load set of mints that appear in a sniper cohort. Small file, fits in RAM."""
    log(f"Loading cohorts from {COHORTS_FILE}")
    cohort_mints = set()
    cohort_size_by_mint = {}
    line_count = 0
    with open(COHORTS_FILE, "r") as f:
        for line in f:
            line_count += 1
            try:
                row = json.loads(line)
                mint = row.get("mint")
                if not mint:
                    continue
                cohort_mints.add(mint)
                wallets = row.get("wallets", [])
                cohort_size_by_mint[mint] = max(
                    cohort_size_by_mint.get(mint, 0),
                    len(wallets) if isinstance(wallets, list) else 0
                )
            except json.JSONDecodeError:
                continue
    log(f"Loaded {line_count} cohort rows -> {len(cohort_mints)} unique cohort mints")
    return cohort_mints, cohort_size_by_mint


def extract_max_multiple(row):
    """
    Extract max price multiple observed post-rejection.
    rejection_outcomes.jsonl rows carry priceChange5m, priceChange1h, priceChange24h
    as percent moves. Convert to multiple.

    Also handle if rows carry a peak_multiple or max_pct field directly.
    """
    # Prefer explicit peak fields if present
    for field in ("peakMultiple", "peak_multiple", "maxMultiple", "max_multiple"):
        v = row.get(field)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)

    # Fall back to price change percents
    max_pct = 0.0
    for field in ("priceChange5m", "priceChange1h", "priceChange24h",
                  "price_change_5m", "price_change_1h", "price_change_24h"):
        v = row.get(field)
        if isinstance(v, (int, float)):
            max_pct = max(max_pct, float(v))

    # Convert +X% to multiple: e.g., +900% = 10x
    return 1.0 + (max_pct / 100.0) if max_pct > 0 else 1.0


def analyze():
    cohort_mints, cohort_size_by_mint = load_cohort_mints()

    log(f"Streaming rejections from {REJECTIONS_FILE}")

    stats_cohort = {"n": 0, "n_winner": 0, "reject_reasons": Counter(),
                    "dex_dist": Counter(), "max_mult_sum": 0.0}
    stats_no_cohort = {"n": 0, "n_winner": 0, "reject_reasons": Counter(),
                       "dex_dist": Counter(), "max_mult_sum": 0.0}

    per_mint_seen = set()
    winners_by_mint_cohort = []
    winners_by_mint_no_cohort = []

    line_count = 0
    with open(REJECTIONS_FILE, "r") as f:
        for line in f:
            line_count += 1
            if line_count % 100_000 == 0:
                log(f"  processed {line_count:,} rejection rows")
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            mint = row.get("mint")
            if not mint:
                continue

            in_cohort = mint in cohort_mints
            reject_reason = row.get("rejectReason") or row.get("reject_reason") or "unknown"
            dex = row.get("dexId") or row.get("dex") or "unknown"
            max_mult = extract_max_multiple(row)
            is_winner = max_mult >= WINNER_MULTIPLE

            target = stats_cohort if in_cohort else stats_no_cohort
            target["n"] += 1
            if is_winner:
                target["n_winner"] += 1
            target["reject_reasons"][reject_reason] += 1
            target["dex_dist"][dex] += 1
            target["max_mult_sum"] += max_mult

            # First-seen mint tracking for CSV
            if mint not in per_mint_seen:
                per_mint_seen.add(mint)
                cohort_size = cohort_size_by_mint.get(mint, 0)
                if in_cohort and is_winner:
                    winners_by_mint_cohort.append(
                        (mint, reject_reason, dex, cohort_size, max_mult)
                    )
                elif not in_cohort and is_winner:
                    winners_by_mint_no_cohort.append(
                        (mint, reject_reason, dex, max_mult)
                    )

    log(f"Total rejection rows processed: {line_count:,}")
    log(f"Cohort-mint rejections: {stats_cohort['n']:,}  "
        f"({stats_cohort['n_winner']:,} winners)")
    log(f"Non-cohort rejections:  {stats_no_cohort['n']:,}  "
        f"({stats_no_cohort['n_winner']:,} winners)")

    # Compute rates
    def rate(d):
        return (d["n_winner"] / d["n"] * 100) if d["n"] > 0 else 0.0

    def mean_mult(d):
        return (d["max_mult_sum"] / d["n"]) if d["n"] > 0 else 0.0

    cohort_rate = rate(stats_cohort)
    no_cohort_rate = rate(stats_no_cohort)
    lift = (cohort_rate / no_cohort_rate) if no_cohort_rate > 0 else float("inf")

    # Write report
    report_path = os.path.join(OUTPUT_DIR, "cohort_rejection_join_report.txt")
    with open(report_path, "w") as f:
        f.write("SNIPER COHORT x REJECTION OUTCOME JOIN\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}Z\n")
        f.write(f"Winner threshold: >= {WINNER_MULTIPLE}x max post-rejection move\n\n")

        f.write("HEADLINE FINDING\n")
        f.write("-" * 60 + "\n")
        f.write(f"Cohort-touched rejections:    "
                f"{stats_cohort['n']:>10,} events, "
                f"{stats_cohort['n_winner']:>6,} winners "
                f"({cohort_rate:.3f}%)\n")
        f.write(f"Cohortless rejections:        "
                f"{stats_no_cohort['n']:>10,} events, "
                f"{stats_no_cohort['n_winner']:>6,} winners "
                f"({no_cohort_rate:.3f}%)\n")
        f.write(f"\nLift (cohort / cohortless):   {lift:.2f}x\n")
        f.write(f"Mean max-multiple, cohort:    {mean_mult(stats_cohort):.3f}\n")
        f.write(f"Mean max-multiple, cohortless: {mean_mult(stats_no_cohort):.3f}\n\n")

        f.write("TOP 10 REJECT REASONS (cohort-touched)\n")
        f.write("-" * 60 + "\n")
        for reason, cnt in stats_cohort["reject_reasons"].most_common(10):
            f.write(f"  {reason:<40} {cnt:>8,}\n")

        f.write("\nTOP 10 REJECT REASONS (cohortless)\n")
        f.write("-" * 60 + "\n")
        for reason, cnt in stats_no_cohort["reject_reasons"].most_common(10):
            f.write(f"  {reason:<40} {cnt:>8,}\n")

        f.write("\nDEX DISTRIBUTION (cohort-touched)\n")
        f.write("-" * 60 + "\n")
        for dex, cnt in stats_cohort["dex_dist"].most_common():
            f.write(f"  {dex:<20} {cnt:>8,}\n")

        f.write("\nDEX DISTRIBUTION (cohortless)\n")
        f.write("-" * 60 + "\n")
        for dex, cnt in stats_no_cohort["dex_dist"].most_common():
            f.write(f"  {dex:<20} {cnt:>8,}\n")

    log(f"Report written: {report_path}")

    # Winners CSV — cohort side (mints with cohort presence that 10x'd after rejection)
    cohort_winners_csv = os.path.join(OUTPUT_DIR, "cohort_winners_by_mint.csv")
    with open(cohort_winners_csv, "w") as f:
        f.write("mint,reject_reason,dex,cohort_wallet_count,max_multiple\n")
        for row in sorted(winners_by_mint_cohort, key=lambda x: -x[4]):
            f.write(f"{row[0]},{row[1]},{row[2]},{row[3]},{row[4]:.3f}\n")
    log(f"Cohort winners CSV: {cohort_winners_csv} "
        f"({len(winners_by_mint_cohort)} rows)")

    # Summary aggregate CSV
    summary_csv = os.path.join(OUTPUT_DIR, "cohort_rejection_summary.csv")
    with open(summary_csv, "w") as f:
        f.write("group,n_rejections,n_winners,winner_pct,mean_max_multiple\n")
        f.write(f"cohort_touched,{stats_cohort['n']},{stats_cohort['n_winner']},"
                f"{cohort_rate:.4f},{mean_mult(stats_cohort):.4f}\n")
        f.write(f"cohortless,{stats_no_cohort['n']},{stats_no_cohort['n_winner']},"
                f"{no_cohort_rate:.4f},{mean_mult(stats_no_cohort):.4f}\n")
    log(f"Summary CSV: {summary_csv}")

    log("DONE")

    # Print headline to stdout
    print()
    print("=" * 60)
    print("HEADLINE")
    print("=" * 60)
    print(f"Cohort-touched winner rate:  {cohort_rate:.3f}%")
    print(f"Cohortless winner rate:      {no_cohort_rate:.3f}%")
    print(f"Lift:                        {lift:.2f}x")
    print("=" * 60)


if __name__ == "__main__":
    try:
        analyze()
    except FileNotFoundError as e:
        log(f"ERROR: input file not found: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        log("Interrupted by user")
        sys.exit(130)
