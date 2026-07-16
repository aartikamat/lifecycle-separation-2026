# lifecycle-separation-2026

Reproducibility scripts for the paper:

**Sniper Cohorts and Algorithmic Filter Rejections in Solana Memecoin Markets: Two-Window Replication of Lifecycle-Stage Population Separation**
Kamat, A. U. (2026). Working paper.

## Zenodo bundle (data + full reproducibility package)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21399918.svg)](https://doi.org/10.5281/zenodo.21399918)

- **Concept DOI (always resolves to latest version):** [10.5281/zenodo.21399918](https://doi.org/10.5281/zenodo.21399918)
- **Version v1 pinned DOI:** [10.5281/zenodo.21399919](https://doi.org/10.5281/zenodo.21399919)

The Zenodo bundle contains the frozen data files, analysis output reports, and full documentation (LICENSE, README, SCHEMA, SHA256SUMS). This GitHub repository mirrors only the analysis scripts for code-first discoverability.

## What's in this repository

```
scripts/
  analyze_cohort_rejection.py         Primary join analysis
  investigate_cohort_disjoint.py      Investigation of the disjoint finding
  investigate_alternatives_ABC.py     Alternative-explanation tests (A/B/C)
  replicate_v2_july.py                v1 vs v2 replication comparison
  analyze_rejection_by_utc_hour.py    UTC hour stratification
  generate_lifecycle_paper_figures.py Figures 1 to 5
  generate_fig6_v1_vs_v2.py           Side-by-side v1 vs v2 figure

LICENSE       CC-BY-4.0
SCHEMA.md     Field definitions for both data streams
```

## How to reproduce the paper

Download the data files from the Zenodo bundle above. Then:

```bash
# Python 3.9+ with matplotlib
pip install matplotlib

# Unzip the Zenodo bundle to a working folder
unzip LIFECYCLE-SEPARATION-2026-v1.zip

# Edit the DATA_DIR variable at the top of each script if needed,
# then run in order
python scripts/analyze_cohort_rejection.py
python scripts/investigate_cohort_disjoint.py
python scripts/investigate_alternatives_ABC.py
python scripts/replicate_v2_july.py
python scripts/analyze_rejection_by_utc_hour.py

# Figures
python scripts/generate_lifecycle_paper_figures.py
python scripts/generate_fig6_v1_vs_v2.py
```

Every number in the paper reproduces byte-for-byte from the frozen data files. Total runtime under 5 minutes on a modest single-vCPU machine.

## Citation

If you use this code or data, please cite the paper AND the dataset:

**Paper:**
Kamat, A. U. (2026). Sniper Cohorts and Algorithmic Filter Rejections in Solana Memecoin Markets: Two-Window Replication of Lifecycle-Stage Population Separation. SSRN Working Paper [ID pending].

**Dataset:**
Kamat, A. U. (2026). LIFECYCLE-SEPARATION-2026-v1: Sniper Cohort and Algorithmic Rejection Datasets [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21399918

## License

CC-BY-4.0. See [LICENSE](LICENSE).

Patent and commercial licensing disclosure: the code and data are released under CC-BY-4.0. The author holds pending USPTO Provisional Patent Applications in the field of algorithmic decentralized-exchange trading and blockchain market microstructure. Commercial re-implementation of specific methodologies covered by pending patent claims may require patent licensing. Academic re-implementation is unaffected. For commercial licensing inquiries: arati.kamat@ieee.org

## Author

Arati Uday Kamat
Independent Researcher, McKinney, TX, USA
ORCID: [0009-0000-4781-312X](https://orcid.org/0009-0000-4781-312X)
