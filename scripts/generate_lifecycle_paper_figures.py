#!/usr/bin/env python3
"""
generate_lifecycle_paper_figures.py

Generates figures for the lifecycle-separation paper.
Runs on the server where data lives, produces 5 PNGs at 200 DPI.

Figures:
  1. venn_cohort_vs_rejection.png     — set overlap visualization
  2. dex_distribution.png              — rejection DEX bar chart
  3. hourly_winner_rate.png            — UTC hour winner rate bar chart
  4. daily_activity_overlap.png        — cohort activity + rejection activity time series
  5. cohort_size_distribution.png      — histogram of cohort n_wallets

Output: analysis/figures/
"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from collections import Counter, defaultdict
from datetime import datetime, timezone

DATA = "data"
OUT = "analysis/figures"
os.makedirs(OUT, exist_ok=True)

COHORTS = f"{DATA}/sniper_cohorts_intra.jsonl"
REJECTIONS = f"{DATA}/rejection_outcomes.jsonl"

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
})


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


def load_cohort_data():
    log("Loading cohort data")
    mints = set()
    sizes = []
    daily = defaultdict(int)
    with open(COHORTS) as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("mint")
            if m:
                mints.add(m)
            n = r.get("n_wallets")
            if isinstance(n, int) and n > 0:
                sizes.append(n)
            ts = get_ts(r)
            if ts:
                day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
                daily[day] += 1
    return mints, sizes, daily


def scan_rejections():
    log("Scanning rejections")
    mints = set()
    dex = Counter()
    daily = defaultdict(int)
    with open(REJECTIONS) as f:
        for i, line in enumerate(f):
            if i % 200_000 == 0:
                log(f"  {i:,} rows")
            try:
                r = json.loads(line)
            except Exception:
                continue
            m = r.get("mint")
            if m:
                mints.add(m)
            d = r.get("dexId") or r.get("dex")
            if d:
                dex[d] += 1
            ts = get_ts(r)
            if ts:
                day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
                daily[day] += 1
    return mints, dex, daily


def fig1_venn(cohort_mints, reject_mints, overlap_count):
    log("Fig 1: Venn diagram")
    fig, ax = plt.subplots(figsize=(8, 5))

    # Two circles roughly scaled by log of set size
    import math
    c_size = math.log10(len(cohort_mints) + 1) * 0.6
    r_size = math.log10(len(reject_mints) + 1) * 0.6

    # Position circles side by side with slight overlap for visual
    c_left = Circle((-0.5, 0), c_size, alpha=0.5, color="#4C72B0", label="Cohort")
    c_right = Circle((0.5 + c_size - r_size, 0), r_size, alpha=0.5,
                     color="#DD8452", label="Rejection")
    ax.add_patch(c_left)
    ax.add_patch(c_right)

    ax.text(-0.5, 0, f"Cohort\nn={len(cohort_mints):,}",
            ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(0.5 + c_size - r_size, 0, f"Rejection\nn={len(reject_mints):,}",
            ha="center", va="center", fontsize=11, fontweight="bold")

    ax.text(0, -c_size - 0.3, f"Overlap: {overlap_count} mints ({overlap_count/len(cohort_mints)*100:.3f}% of cohort)",
            ha="center", va="center", fontsize=10, style="italic")

    ax.set_xlim(-2, 2)
    ax.set_ylim(-c_size - 0.6, c_size + 0.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Population separation: cohort vs rejection\n(2026-06-11 to 2026-06-25)")

    path = f"{OUT}/fig1_venn_cohort_vs_rejection.png"
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    log(f"  saved {path}")


def fig2_dex_distribution(dex_counts):
    log("Fig 2: DEX distribution")
    fig, ax = plt.subplots(figsize=(8, 5))
    items = dex_counts.most_common(6)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2", "#937860"]

    bars = ax.bar(labels, values, color=colors[:len(items)])
    ax.set_ylabel("Rejection rows")
    ax.set_title("Rejection stream by DEX venue\n(712,656 rows, full three-month window)")

    # Add value labels
    for bar, v in zip(bars, values):
        pct = v / sum(values) * 100
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                f"{v:,}\n({pct:.1f}%)", ha="center", va="bottom", fontsize=9)

    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=15)
    path = f"{OUT}/fig2_dex_distribution.png"
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    log(f"  saved {path}")


def fig3_hourly_winner_rate():
    log("Fig 3: Hourly winner rate")
    csv_path = "analysis/rejection_hour_of_day.csv"
    if not os.path.exists(csv_path):
        log(f"  {csv_path} not found, skipping")
        return
    hours, rates, ns = [], [], []
    with open(csv_path) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split(",")
            hours.append(int(parts[0]))
            ns.append(int(parts[1]))
            rates.append(float(parts[3]))

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(hours, rates, color="#4C72B0", alpha=0.8)
    ax.axhline(sum(rates) / len(rates), color="#C44E52", linestyle="--", alpha=0.6,
               label=f"Mean {sum(rates)/len(rates):.2f}%")
    ax.set_xlabel("UTC hour of rejection")
    ax.set_ylabel("Winner rate (>=10x post-rejection peak), %")
    ax.set_title("Counterfactual winner rate by UTC hour\n(chi-sq=22.26, p>0.05 vs uniform)")
    ax.set_xticks(range(24))
    ax.grid(True, alpha=0.3, axis="y")
    ax.legend()

    # Annotate max and min hours
    max_i = rates.index(max(rates))
    min_i = rates.index(min(rates))
    ax.annotate(f"{rates[max_i]:.2f}%", (hours[max_i], rates[max_i]),
                textcoords="offset points", xytext=(0, 5),
                ha="center", fontsize=8, fontweight="bold", color="#2A6099")
    ax.annotate(f"{rates[min_i]:.2f}%", (hours[min_i], rates[min_i]),
                textcoords="offset points", xytext=(0, 5),
                ha="center", fontsize=8, fontweight="bold", color="#C44E52")

    path = f"{OUT}/fig3_hourly_winner_rate.png"
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    log(f"  saved {path}")


def fig4_daily_activity(cohort_daily, reject_daily):
    log("Fig 4: Daily activity overlap")
    all_days = sorted(set(cohort_daily.keys()) | set(reject_daily.keys()))
    c_vals = [cohort_daily.get(d, 0) for d in all_days]
    r_vals = [reject_daily.get(d, 0) for d in all_days]

    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.plot(all_days, c_vals, color="#4C72B0", linewidth=2, label="Cohort detections (daily)")
    ax1.set_ylabel("Cohort detections", color="#4C72B0")
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    ax2 = ax1.twinx()
    ax2.plot(all_days, r_vals, color="#DD8452", linewidth=2, label="Rejection rows (daily)")
    ax2.set_ylabel("Rejection rows", color="#DD8452")
    ax2.tick_params(axis="y", labelcolor="#DD8452")

    ax1.set_title("Daily activity: cohort detections vs rejection rows\nShaded: cohort observation window (2026-06-11 to 2026-06-25)")
    ax1.set_xlabel("Date (UTC)")

    # Shade cohort window
    cohort_start = "2026-06-11"
    cohort_end = "2026-06-25"
    if cohort_start in all_days and cohort_end in all_days:
        ax1.axvspan(cohort_start, cohort_end, alpha=0.15, color="#4C72B0")

    # Sparse x-ticks
    step = max(1, len(all_days) // 12)
    ax1.set_xticks(all_days[::step])
    plt.xticks(rotation=45, ha="right")
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    path = f"{OUT}/fig4_daily_activity_overlap.png"
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    log(f"  saved {path}")


def fig5_cohort_size(sizes):
    log("Fig 5: Cohort size distribution")
    fig, ax = plt.subplots(figsize=(8, 5))
    if not sizes:
        log("  no sizes data, skipping")
        return
    max_bin = min(max(sizes), 50)
    ax.hist(sizes, bins=range(0, max_bin + 2), color="#4C72B0", alpha=0.8, edgecolor="white")
    ax.set_xlabel("Cohort size (n_wallets)")
    ax.set_ylabel("Frequency")
    ax.set_title(f"Cohort size distribution (n={len(sizes):,} cohort observations)\nMedian={sorted(sizes)[len(sizes)//2]}, Max={max(sizes)}")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, axis="y")
    path = f"{OUT}/fig5_cohort_size_distribution.png"
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    log(f"  saved {path}")


def main():
    cohort_mints, cohort_sizes, cohort_daily = load_cohort_data()
    reject_mints, reject_dex, reject_daily = scan_rejections()

    overlap = len(cohort_mints & reject_mints)
    log(f"Cohort={len(cohort_mints):,}  Rejection={len(reject_mints):,}  Overlap={overlap}")

    fig1_venn(cohort_mints, reject_mints, overlap)
    fig2_dex_distribution(reject_dex)
    fig3_hourly_winner_rate()
    fig4_daily_activity(cohort_daily, reject_daily)
    fig5_cohort_size(cohort_sizes)

    log("All figures generated")


if __name__ == "__main__":
    main()
