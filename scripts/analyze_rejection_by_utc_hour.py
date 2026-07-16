#!/usr/bin/env python3
"""
analyze_rejection_by_utc_hour.py

UTC hour-of-day stratification of the 712K rejection outcomes.
Tests: "does the counterfactual winner rate vary by UTC hour?"

Publishable as short-form letter (JFDS Letters or similar).
Directly extends the Hour-Aware Risk paper into the rejection domain.

Output: /root/solana-bot/analysis/rejection_hour_of_day_report.txt
        /root/solana-bot/analysis/rejection_hour_of_day.csv
"""

import json
import os
from datetime import datetime, timezone
from collections import defaultdict

DATA = "/root/solana-bot/data"
OUT = "/root/solana-bot/analysis"
os.makedirs(OUT, exist_ok=True)

REJECTIONS = f"{DATA}/rejection_outcomes.jsonl"

WINNER_MULT = 10.0


def log(m):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {m}", flush=True)


def get_ts(row):
    for k in ("rejectTs", "sampleTs", "ts", "timestamp"):
        v = row.get(k)
        if isinstance(v, (int, float)) and v > 1_000_000_000:
            return v / 1000 if v > 1e12 else v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()
            except:
                continue
    return None


def max_multiple(row):
    for f in ("peakMultiple", "peak_multiple", "maxMultiple", "max_multiple"):
        v = row.get(f)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
    max_pct = 0.0
    for f in ("priceChange24h", "priceChange1h", "priceChange5m",
              "price_change_24h", "price_change_1h", "price_change_5m"):
        v = row.get(f)
        if isinstance(v, (int, float)):
            max_pct = max(max_pct, float(v))
    return 1.0 + (max_pct / 100.0) if max_pct > 0 else 1.0


def main():
    log("Streaming rejections for UTC-hour stratification")

    hour_stats = defaultdict(lambda: {"n": 0, "winners": 0, "mult_sum": 0.0})
    dow_stats = defaultdict(lambda: {"n": 0, "winners": 0})
    seen_mint_hour = set()  # dedupe by (mint, hour)

    total = 0
    ts_missing = 0

    with open(REJECTIONS) as f:
        for line in f:
            total += 1
            if total % 200_000 == 0:
                log(f"  {total:,} rows scanned")
            try:
                r = json.loads(line)
            except:
                continue
            ts = get_ts(r)
            if ts is None:
                ts_missing += 1
                continue
            mint = r.get("mint")
            dt = datetime.fromtimestamp(ts, timezone.utc)
            hour = dt.hour
            dow = dt.weekday()  # 0=Mon
            mult = max_multiple(r)
            is_winner = mult >= WINNER_MULT

            # Dedup: count each mint-hour once for winner rate
            key = (mint, hour, int(ts // 3600))
            if key in seen_mint_hour:
                continue
            seen_mint_hour.add(key)

            hour_stats[hour]["n"] += 1
            hour_stats[hour]["mult_sum"] += mult
            dow_stats[dow]["n"] += 1
            if is_winner:
                hour_stats[hour]["winners"] += 1
                dow_stats[dow]["winners"] += 1

    log(f"Total rows: {total:,}; ts_missing: {ts_missing:,}; "
        f"unique mint-hour keys: {len(seen_mint_hour):,}")

    # Compute rates
    hour_rates = {}
    for h in range(24):
        s = hour_stats[h]
        rate = (s["winners"] / s["n"] * 100) if s["n"] > 0 else 0.0
        mean_mult = (s["mult_sum"] / s["n"]) if s["n"] > 0 else 0.0
        hour_rates[h] = {
            "n": s["n"], "winners": s["winners"],
            "winner_pct": rate, "mean_multiple": mean_mult
        }

    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    dow_rates = {}
    for d in range(7):
        s = dow_stats[d]
        rate = (s["winners"] / s["n"] * 100) if s["n"] > 0 else 0.0
        dow_rates[dow_names[d]] = {"n": s["n"], "winners": s["winners"], "winner_pct": rate}

    # Chi-squared for hour uniformity
    total_n = sum(hour_stats[h]["n"] for h in range(24))
    total_w = sum(hour_stats[h]["winners"] for h in range(24))
    overall_rate = (total_w / total_n * 100) if total_n > 0 else 0.0
    expected_per_hour = total_w / 24
    chi2 = 0.0
    for h in range(24):
        obs = hour_stats[h]["winners"]
        if expected_per_hour > 0:
            chi2 += (obs - expected_per_hour) ** 2 / expected_per_hour

    # Write report
    report_path = f"{OUT}/rejection_hour_of_day_report.txt"
    with open(report_path, "w") as f:
        f.write("REJECTION OUTCOMES BY UTC HOUR OF DAY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Winner threshold: >={WINNER_MULT}x max post-rejection move\n\n")

        f.write(f"Overall: {total_n:,} unique mint-hour observations, "
                f"{total_w:,} winners, {overall_rate:.3f}%\n\n")

        f.write("BY UTC HOUR\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Hour':<6}{'N':>10}{'Winners':>10}{'Winner %':>12}{'Mean Mult':>12}\n")
        for h in range(24):
            s = hour_rates[h]
            f.write(f"{h:<6}{s['n']:>10,}{s['winners']:>10,}"
                    f"{s['winner_pct']:>12.3f}{s['mean_multiple']:>12.3f}\n")

        f.write(f"\nChi-squared (uniformity across 24 hours): {chi2:.2f}\n")
        f.write(f"df=23; critical value @ p=0.05: 35.17; @ p=0.01: 41.64\n")
        if chi2 > 41.64:
            f.write("VERDICT: Hourly distribution significantly non-uniform (p<0.01)\n")
        elif chi2 > 35.17:
            f.write("VERDICT: Hourly distribution non-uniform (p<0.05)\n")
        else:
            f.write("VERDICT: Cannot reject uniformity at p=0.05\n")

        f.write("\nBY DAY OF WEEK\n")
        f.write("-" * 60 + "\n")
        f.write(f"{'Day':<6}{'N':>10}{'Winners':>10}{'Winner %':>12}\n")
        for d in dow_names:
            s = dow_rates[d]
            f.write(f"{d:<6}{s['n']:>10,}{s['winners']:>10,}{s['winner_pct']:>12.3f}\n")

        # Top / bottom hours
        sorted_hours = sorted(range(24), key=lambda h: -hour_rates[h]["winner_pct"])
        f.write("\nTOP 5 HOURS BY WINNER RATE\n")
        for h in sorted_hours[:5]:
            s = hour_rates[h]
            f.write(f"  {h:02d} UTC: {s['winner_pct']:.3f}% ({s['winners']:,}/{s['n']:,})\n")
        f.write("\nBOTTOM 5 HOURS BY WINNER RATE\n")
        for h in sorted_hours[-5:]:
            s = hour_rates[h]
            f.write(f"  {h:02d} UTC: {s['winner_pct']:.3f}% ({s['winners']:,}/{s['n']:,})\n")

    # CSV
    csv_path = f"{OUT}/rejection_hour_of_day.csv"
    with open(csv_path, "w") as f:
        f.write("hour_utc,n_rejections,n_winners,winner_pct,mean_max_multiple\n")
        for h in range(24):
            s = hour_rates[h]
            f.write(f"{h},{s['n']},{s['winners']},{s['winner_pct']:.4f},"
                    f"{s['mean_multiple']:.4f}\n")

    log(f"Report: {report_path}")
    log(f"CSV: {csv_path}")

    print()
    print("=" * 60)
    print("HEADLINE")
    print("=" * 60)
    print(f"Overall winner rate: {overall_rate:.3f}% ({total_w:,}/{total_n:,})")
    print(f"Chi-squared (24-hour uniformity): {chi2:.2f} (crit @ p=0.05: 35.17)")
    top_str = ", ".join(f"{h:02d}={hour_rates[h]['winner_pct']:.3f}%" for h in sorted_hours[:3])
    bot_str = ", ".join(f"{h:02d}={hour_rates[h]['winner_pct']:.3f}%" for h in sorted_hours[-3:])
    print(f"Best 3 hours: {top_str}")
    print(f"Worst 3 hours: {bot_str}")


if __name__ == "__main__":
    main()
