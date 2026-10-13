# lifecycle-separation-2026

Code repository for the paper:

**Do Two On-Chain Observation Pipelines See the Same Tokens? Cross-Pipeline Coverage on the Solana pump.fun Launchpad**
Kamat, A. U. (2026). arXiv:2609.18975. https://doi.org/10.48550/arXiv.2609.18975

(Earlier versions of the paper were titled "Sniper Cohorts and Algorithmic Filter Rejections in Solana Memecoin Markets".)

> **Note:** the current version of the paper reproduces from the Zenodo package `cross_pipeline_coverage_v2.zip` (see below), not from the scripts in this repository. The seven scripts here are the earlier version 1 analysis (Zenodo version 1) and are kept for the record.

## Zenodo package (data + full reproducibility package)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21399918.svg)](https://doi.org/10.5281/zenodo.21399918)

- **Concept DOI (always resolves to the latest version):** [10.5281/zenodo.21399918](https://doi.org/10.5281/zenodo.21399918)
- **Current file:** `cross_pipeline_coverage_v2.zip` (version 2.0.0, 23 September 2026)

The package contains the frozen input files, the two scripts used for the current paper (`reconstruct_overlap.py` and `verify_red_reject_containment.py`), the expected outputs, the figure, documentation (README, data dictionary, number-provenance table, CHANGELOG), a `SHA256SUMS` checksum file, and separate licence files for code and data.

## How to reproduce the paper

Download `cross_pipeline_coverage_v2.zip` from the concept DOI above. Then:

```bash
# Python 3.12+; the scripts use only the Python standard library
unzip cross_pipeline_coverage_v2.zip
cd cross_pipeline_coverage_v2
sha256sum -c SHA256SUMS      # every line should print OK
bash run.sh                  # on Windows: powershell -File run.ps1
```

`run.sh` checks the input checksums, rewrites every file in `outputs/`, and exits with a non-zero code unless its built-in checks on the reported counts pass. A re-run in October 2026 rewrote all 14 output files byte-identical to the deposited copies.

## What's in this repository (earlier version 1 analysis)

The seven scripts below are the earlier version 1 analysis, written for the data files of Zenodo version 1. Those files are superseded and are not part of the current Zenodo package, so the scripts are kept for the record and are not the way to reproduce the current paper. In the script names, "v1" and "v2" refer to the two data windows of that analysis, not to versions of the paper.

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

## Citation

If you use this code or data, please cite the paper AND the dataset:

**Paper:**
Kamat, A. U. (2026). Do Two On-Chain Observation Pipelines See the Same Tokens? Cross-Pipeline Coverage on the Solana pump.fun Launchpad. arXiv:2609.18975. https://doi.org/10.48550/arXiv.2609.18975

**Dataset:**
Kamat, A. U. (2026). Cross-Pipeline Coverage on the Solana pump.fun Launchpad: Reproducibility Package [Data set]. Zenodo. https://doi.org/10.5281/zenodo.21399918

## License

CC-BY-4.0. See [LICENSE](LICENSE).

## Author

Arati Uday Kamat
Independent Researcher
ORCID: [0009-0000-4781-312X](https://orcid.org/0009-0000-4781-312X)
