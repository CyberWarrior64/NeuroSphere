# NeuroSphere Research Figures

These figures are prepared for insertion into the project report or a research paper. Each is provided as a high-resolution PNG (300 dpi) and an editable vector SVG. Metric values are loaded from the evaluation JSON files in the AI Engine; packet-parity values are read from the AI Engine README.

## Figures and suggested captions

### Figure 1 — Random-split model metrics

Attack-class precision, recall, and F1 for Random Forest and Isolation Forest on a filtered, stratified 60/20/20 random split of CICIDS2017 flows. The test set contains 56,993 flows from 284,963 filtered rows. Conflict patterns and exact feature duplicates were removed. The random split is not capture-day-disjoint and should not be presented as evidence of cross-day generalization.

Files: `figure_1_random_split_metrics.png` and `figure_1_random_split_metrics.svg`.

### Figure 2 — Friday capture-day holdout

Attack-class precision, recall, and F1, with false-positive rates shown separately, for Random Forest V2, Isolation Forest V2, and offline Hybrid OR/AND combinations. Models were trained on Monday through Wednesday data, thresholds were selected on Thursday, and the frozen models were evaluated on 702,164 Friday flows. This uses the same CICIDS2017 benchmark and is not external-network validation. Hybrid OR and AND are analysis-only combinations, not separate deployed models.

Files: `figure_2_friday_holdout_metrics.png` and `figure_2_friday_holdout_metrics.svg`.

### Figure 3 — Packet feature parity

Feature-cell agreement and complete 67-feature-vector agreement in a bounded comparison using the first 100,000 packets of the Monday CICIDS2017 capture. The core-exact subset (n=4,899) includes only flows whose duration, packet counts, and directional payload totals match. Its agreement values are conditional on that selection and do not establish parity with the exact training-generator release or with independent captures.

Files: `figure_3_packet_feature_parity.png` and `figure_3_packet_feature_parity.svg`.

## Data sources

- `../../ai-engine/datasets/processed/validated_randomsplit_results/evaluation.json` — filtered random-split evaluation, including thresholds and false-positive rates.
- `../../ai-engine/datasets/processed/hybrid_v2_friday_holdout_results/hybrid_v2_friday_holdout_summary.json` — Friday capture-day holdout evaluation.
- `../../ai-engine/README.md` — bounded packet-feature parity summary.
- `source_metrics.csv` — values used in the figures for convenient checking.

Rebuild the figures from the repository root with Python and Pillow installed:

```powershell
python docs/research_figures/generate_figures.py
```

The existing project report has a fixed page plan and figure list. These assets are supplied separately so they can be inserted where needed and the report page references can be updated to match the final layout.
