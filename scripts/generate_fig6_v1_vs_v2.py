#!/usr/bin/env python3
"""
generate_fig6_v1_vs_v2.py

Figure 6: Side-by-side replication comparison of v1 (June) vs v2 (July).
Two panels:
  A) Absolute counts (log scale) - cohort, rejection, overlap
  B) Overlap percentages - as % of cohort AND as % of rejection
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

OUT = "analysis/figures"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.family": "sans-serif",
    "font.size": 10,
})

# Verified numbers from replication analysis
data = {
    "v1 (Jun 11 to 25)": {
        "cohort": 20162,
        "rejection": 83,
        "overlap": 2,
        "overlap_pct_of_cohort": 0.010,
        "overlap_pct_of_rejection": 2.410,
    },
    "v2 (Jun 29 to Jul 16)": {
        "cohort": 623,
        "rejection": 1743,
        "overlap": 5,
        "overlap_pct_of_cohort": 0.803,
        "overlap_pct_of_rejection": 0.287,
    },
}

versions = list(data.keys())
metrics_abs = ["Cohort mints", "Rejection mints", "Overlap mints"]
values_v1 = [data["v1 (Jun 11 to 25)"]["cohort"],
             data["v1 (Jun 11 to 25)"]["rejection"],
             data["v1 (Jun 11 to 25)"]["overlap"]]
values_v2 = [data["v2 (Jun 29 to Jul 16)"]["cohort"],
             data["v2 (Jun 29 to Jul 16)"]["rejection"],
             data["v2 (Jun 29 to Jul 16)"]["overlap"]]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

# ============ PANEL A: Absolute counts (log scale) ============
x = np.arange(len(metrics_abs))
width = 0.38
bars_v1 = ax1.bar(x - width/2, values_v1, width, label="v1 (June)",
                   color="#4C72B0", alpha=0.85, edgecolor="white")
bars_v2 = ax1.bar(x + width/2, values_v2, width, label="v2 (July)",
                   color="#DD8452", alpha=0.85, edgecolor="white")

# Add value labels on top of bars
for bar, v in zip(bars_v1, values_v1):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.15,
             f"{v:,}", ha="center", va="bottom", fontsize=9, fontweight="bold",
             color="#2A4A70")
for bar, v in zip(bars_v2, values_v2):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.15,
             f"{v:,}", ha="center", va="bottom", fontsize=9, fontweight="bold",
             color="#B8562A")

ax1.set_xticks(x)
ax1.set_xticklabels(metrics_abs)
ax1.set_yscale("log")
ax1.set_ylabel("Unique mints (log scale)")
ax1.set_title("A. Absolute counts across replication windows")
ax1.legend(loc="upper right", frameon=True)
ax1.grid(True, alpha=0.3, axis="y", which="both")
ax1.set_ylim(0.5, 100000)

# ============ PANEL B: Overlap percentages ============
pct_labels = ["as % of cohort", "as % of rejection"]
pct_v1 = [data["v1 (Jun 11 to 25)"]["overlap_pct_of_cohort"],
          data["v1 (Jun 11 to 25)"]["overlap_pct_of_rejection"]]
pct_v2 = [data["v2 (Jun 29 to Jul 16)"]["overlap_pct_of_cohort"],
          data["v2 (Jun 29 to Jul 16)"]["overlap_pct_of_rejection"]]

x2 = np.arange(len(pct_labels))
bars_v1_pct = ax2.bar(x2 - width/2, pct_v1, width, label="v1 (June)",
                       color="#4C72B0", alpha=0.85, edgecolor="white")
bars_v2_pct = ax2.bar(x2 + width/2, pct_v2, width, label="v2 (July)",
                       color="#DD8452", alpha=0.85, edgecolor="white")

# Value labels
for bar, v in zip(bars_v1_pct, pct_v1):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f"{v:.3f}%", ha="center", va="bottom", fontsize=9, fontweight="bold",
             color="#2A4A70")
for bar, v in zip(bars_v2_pct, pct_v2):
    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f"{v:.3f}%", ha="center", va="bottom", fontsize=9, fontweight="bold",
             color="#B8562A")

# Add horizontal line at 1% for context
ax2.axhline(1.0, color="red", linestyle="--", alpha=0.5, linewidth=1)
ax2.text(1.4, 1.05, "1% threshold", color="red", fontsize=8, style="italic")

ax2.set_xticks(x2)
ax2.set_xticklabels(pct_labels)
ax2.set_ylabel("Overlap percentage")
ax2.set_title("B. Overlap magnitude (both windows below 1% and 3%)")
ax2.legend(loc="upper right", frameon=True)
ax2.grid(True, alpha=0.3, axis="y")
ax2.set_ylim(0, 3.0)

# Overall figure title
fig.suptitle("Figure 6. Two-window replication: v1 (June 2026) vs v2 (July 2026)\n"
             "Structural finding replicates across different pipeline versions and observation windows",
             fontsize=11, y=1.00)

plt.tight_layout()
path = f"{OUT}/fig6_v1_vs_v2_replication.png"
plt.savefig(path, bbox_inches="tight")
plt.close()
print(f"Saved: {path}")
