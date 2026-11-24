# Rural 5G Coverage Analyzer — ARA Field Measurement Datasets

A small, reproducible analysis tool that turns raw RF field measurements into a
coverage report: signal-strength classes, a geographic grid of median RSRP,
weak-coverage zones, and a SINR → throughput cross-tabulation.

It was built and run on the two public measurement datasets published by the
**ARA Wireless Living Lab** (Iowa State University) — a real, field-deployed
Ericsson COTS 5G network (band n77) in rural Iowa, USA.

## What it does

**Dataset 1 — spatio-temporal RSRP** (56,122 outdoor UE samples)

- Geographic grid of ~0.005° × 0.005° cells (~550 m × ~460 m) with median RSRP per cell.
- **Weak zones:** cells with median RSRP < −110 dBm and at least 30 samples,
  listed with center coordinates and sample counts.
- Share of samples per coverage class: excellent (≥ −80 dBm), good (−90 to −80),
  fair (−100 to −90), weak (−110 to −100), very weak (< −110).

**Dataset 2 — UE channel measurements** (7,144 rows)

- Distribution of samples per SINR class: excellent (≥ 20 dB), good (10–20),
  fair (0–10), poor (< 0).
- SINR → median throughput cross-tab (downlink and uplink separately), using
  only rows that carry both measurements, with the n of each class reported.

## Headline results (run of 2026-11-24, full report in `informe.md`)

- Coverage classes (Dataset 1): excellent 8.14% · good 12.30% · fair 24.31% ·
  weak 31.20% · very weak 24.04%.
- **112 weak zones** found; the weakest cell (median −124.2 dBm) sits at
  42.03250, −93.72250.
- Median **uplink** throughput is markedly lower in the low-SINR classes of
  this sample (62.9 → 62.9 → 41.9 → 10.9 Mbps across excellent / good / fair /
  poor), while median downlink changes little (232 → 192 Mbps). The table
  reports what the sample shows; no cause is attributed.

## What this is not

- It is **not an rApp or xApp**: it does not run on a RIC and consumes no O-RAN interfaces.
- The inputs are **per-sample RF measurements** from a field UE — not an
  operator's 15-minute PM counters or FM alarms. This tool characterizes
  measured coverage and link quality; it does not validate RAN applications.
- Class thresholds are common engineering criteria, not a certification.

## Data and provenance

| Set | Dataset | DOI |
|---|---|---|
| 1 | ARA COTS 5G NR Spatio-Temporal RSRP Measurement Dataset | [10.21227/7np5-4e05](https://doi.org/10.21227/7np5-4e05) |
| 2 | ARA Rural COTS 5G NR UE Measurement Dataset | [10.21227/p2a8-f326](https://doi.org/10.21227/p2a8-f326) |

The datasets are **not** redistributed in this repository. They are available
from IEEE DataPort under its terms. Declared completeness: in Dataset 1, 6.9% of
rows carry no coordinates (the grid uses the 52,243 georeferenced samples; RSRP
has no missing values). In Dataset 2, ~40% of rows carry no radio block and
~56% carry no throughput; every table in the report states its own n.

## How to run

Requirements: Python 3. `analizador.py` additionally needs pandas;
`analizador_stdlib.py` uses only the standard library and produces an
identical report (verified 2026-11-24: same classes, same 112 weak zones,
same SINR → throughput cross-tab).

```bash
# Point the tool at your copies of the two CSVs:
ARA_SET1_CSV=/path/to/ARA_COTS_5G_NR_Spatio_Temporal_Dataset.csv \
ARA_SET2_CSV=/path/to/COTS.csv \
python3 analizador_stdlib.py        # writes informe-stdlib.md

python3 analizador.py               # pandas version, writes informe.md
```

## Files

- `analizador.py` — the tool (pandas version).
- `analizador_stdlib.py` — the same tool, standard library only.
- `informe.md` — the full report generated on the real data on 2026-11-24 (in Spanish).
- `LICENSE` — MIT. The license covers this repository's code only; the ARA
  datasets are not part of this repository and remain under the terms of
  IEEE DataPort / ARA — they are cited by DOI, never redistributed here.

## Author

Rogelio Sanz — radio access network engineer and independent researcher.
LinkedIn: https://mx.linkedin.com/in/rogeliosanz
