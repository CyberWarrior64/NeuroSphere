# NeuroSphere AI Engine

FastAPI service for network traffic detection using the project's saved
Isolation Forest and hybrid V2 models.

## Run the existing environment

From this directory on the Ubuntu host:

    ./run-api.sh

The launcher puts temporary files under /mnt/neurosphere/tmp by default so inference does not fill the 16 GB root filesystem. Override NS_AI_TMPDIR if that storage path changes. The app loads model and preprocessing artifacts at startup. Keep the files in saved_models/ and datasets/processed/ in place.

The browser dashboard is served at http://127.0.0.1:8000/. It shows service/model status and submits a CIC-IDS2017 67-feature JSON flow to the Hybrid V2 endpoint; it does not capture traffic. To view it from Windows while the API is running on Ubuntu, open PowerShell and start an SSH tunnel with:

    ssh -L 8000:127.0.0.1:8000 cse-cy-02@100.70.85.104

Then open http://127.0.0.1:8000/ in the Windows browser. Keep that PowerShell window open while using the dashboard.

The API is available at http://127.0.0.1:8000. Interactive API documentation
is at /docs. Useful endpoints:

- GET /health - service health
- GET /gpu - optional PyTorch and NVIDIA GPU information
- POST /api/v1/detect - legacy Isolation Forest endpoint
- POST /api/v1/detect/v2 - CIC-IDS2017 hybrid detector
- POST /api/v1/detect/validated-randomsplit - experimental validated-data models
- GET /api/v1/capture/cicflowmeter-python/readiness - adapter support and known parity gaps
- POST /api/v1/detect/cicflowmeter-python - experimental CICFlowMeter Python input adapter

The detector uses scikit-learn; PyTorch is optional. The GPU endpoint reports
available NVIDIA information when the relevant runtime tools are installed.

## Dependencies

requirements.txt records the direct package versions present in the existing
working environment. For a fresh environment, use Python 3.12, create a virtual
environment, and install that file. Installing packages is not needed to run
the already configured .venv.

Keep the API bound to loopback unless it is protected by an authenticated
gateway. For remote access, use an SSH tunnel instead of exposing the service
port directly.

## Experimental live CICFlowMeter input

Start the API in one terminal using the command above. In another terminal, send completed flows from the installed CICFlowMeter Python 0.5.0 capture tool to the local API (replace the interface name if needed):

    .venv/bin/python -m app.feature_extraction.run_reference_capture -i enp0s31f6 -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python

To process a saved PCAP/PCAPNG file without capturing live traffic, use the -f option instead of -i, for example:

    .venv/bin/python -m app.feature_extraction.run_reference_capture -f datasets/reference_pcaps/Monday-first-20000.pcap -u http://127.0.0.1:8000/api/v1/detect/cicflowmeter-python

The readiness endpoint includes a feature-by-feature parity audit and source links. The packet adapter recalculates payload, header, timing, ratio, subflow, initial-window, and active/idle fields from raw packets, with several formulas calibrated against the CICIDS2017 training table. A bounded comparison against the first 100,000 packets of Monday traffic found 92.17% feature-cell agreement across 5,831 unique direct flows; 4,547 flows matched all 67 fields. Header-derived fields agreed on 92.30% of compared cells; the best tested candidate carries the preceding TCP header length into UDP fields, an empirical inference. See `datasets/reference_pcaps/Monday-first-100000-feature-parity.json` and rerun with `.venv/bin/python -m app.feature_extraction.compare_training_reference`. Among the 4,899 flows with exact core duration/count/payload fields, 99.62% of feature cells matched and 92.81% matched all 67 fields; this points to flow segmentation as a major remaining source of differences, though that explanation is not proven. That comparison alone does not establish parity with the exact training-generator release, full flow boundaries, or external-capture quality; see the capture-day holdout section below. Use for research only; do not automate blocking or alert escalation. Keep the API bound to loopback.

Supplemental distributed-window comparison: `datasets/reference_pcaps/spaced-windows-25k/results-final/spaced-windows-parity-summary.json` compares four disjoint 25,000-packet windows spread across the full 11.7-million-packet Monday capture. The calibrated session produced 3,905 unique direct matches, 88.90% feature-cell agreement, 3,042 exact core rows, and 2,700 complete 67-feature vectors. A candidate using current upstream FIN handling produced 4,085 matches, 89.85% cell agreement, and 3,268 exact core rows; its complete-vector count stayed at 2,700. The candidate remains experimental and has not replaced the active session. Window edges can truncate flows; one window produced only 21 direct matches. This comparison uses benign traffic from the model's training source and does not establish feature parity or attack-detection quality.

## Friday raw-PCAP adapter sample

The broad offline replay used datasets/reference_pcaps/friday-reference/Friday-WorkingHours-attack-windows.pcapng, a 3.98 GB slice of 15 selected Bot, PortScan, and DDoS windows. The adapter processed 5,077,592 TCP/UDP packets and emitted 442,889 flows. The reference labels are minute-resolution (all 703,245 combined Friday rows are minute-aligned). Matching unique direct source/destination IPs, ports, protocol, and UTC minute produced 354,199 unique matches across 549,787 reference rows in the selected windows.

Attack-row match coverage was 99.90% for PortScan (158,623/158,785), 31.38% for DDoS (40,177/128,027), and 40.84% for Bot (709/1,736). On matched rows, 84.11% of feature cells agreed; 278,577 rows matched five core fields and 104,956 matched all 67 fields. ACK, SYN, PSH, and RST count agreement was 31.6%, 32.3%, 32.5%, and 41.5% respectively. Feature parity remains unverified, and the selected windows do not represent the full Friday capture. The baseline diagnostic is datasets/reference_pcaps/friday-reference/Friday-attack-windows-minute-key-baseline-diagnostics.json.

At previously frozen thresholds, Random Forest recall was 20.32% with 0.49% FPR; Isolation Forest recall was 20.05% with 1.51% FPR. The Random Forest detected all 40,177 matched DDoS rows, 367 of 158,623 PortScan rows, and none of the 709 Bot rows. These results are diagnostic on the same CICIDS2017 benchmark; they do not establish full-day or external-capture performance. Research only; do not automate blocking or alert escalation.

The readiness endpoint uses datasets/reference_pcaps/friday-reference/Friday-attack-windows-minute-key-evaluation.json. The earlier two-window core result is retained in Friday-novel-attack-core-minute-key-evaluation.json. The first one-second-key diagnostic is retained in Friday-novel-attack-core-evaluation.json.

### TCP flag-count and column-order investigation

An independent CICIDS2017 case study reports that the original generator incremented each TCP flag count only for the first flow packet, so the training CSV flag fields are binary; the tool was fixed in 2019. The adapter now has an opt-in `--flag-count-mode first_packet` extraction candidate. Its default remains `all_packets`, and the live API still uses the default mapping and mode. On the Monday first-100,000-packet sample, the candidate reached 92.73% feature-cell agreement versus 92.17% for the existing calibrated output and matched 15 more complete 67-feature vectors (4,562 vs 4,547). The core exact-match count remained 4,899. See `datasets/reference_pcaps/Monday-first-100000-first-packet-flags-parity.json`. This small same-source comparison is preliminary. On a separate two-window Friday Bot/PortScan core capture, first-packet flag counts plus an evaluation-only legacy-order-informed mapping reached 97.17% feature-cell agreement across 203,007 unique matches, with 190,862 exact-core rows and 186,815 rows matching all 67 features. The baseline all-packet/current-mapping run reached 92.34% cell agreement and 36,260 complete vectors. The candidate changes only aggregate flag-count mapping; directional PSH/URG fields remain unchanged and unverified. This is still a bounded sample from the same benchmark and excludes DDoS. See `datasets/reference_pcaps/friday-reference/Friday-novel-attack-core-first-packet-flags-legacy-order-candidate-evaluation.json`. The independent study says the original generator counted flags only on the first flow packet and documents the directional PSH/URG issues as well. Source: [WTMC2021 extended documentation](https://intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html#tcp-flag-count).

The earlier all-packet field-order candidate raised aggregate cell agreement on the broad Friday slice from 84.11% to 86.35%, but added only 43 complete 67-feature rows; that report is `datasets/reference_pcaps/friday-reference/Friday-attack-windows-minute-key-empirical-flag-candidate-fixed-diagnostics.json`. Its high all-row flag agreement was mostly caused by zero-valued fields and did not validate the mapping.

The first-packet candidate changes the evidence: on exact-core rows in the two-window Bot/PortScan capture, the legacy-order-informed SYN/PSH/RST mapping matched those three reference columns exactly, and adding FIN/URG remapping produced 97.17% overall cell agreement and 186,815 complete vectors. On this bounded sample, Random Forest recall remained 0.18% (0.45% FPR) and Isolation Forest recall 0.034% (0.42% FPR) at their frozen thresholds. Feature parity gains do not improve the detectors' poor results on these held-out attack families. The full selected Friday-window replay (5,077,592 packets; 442,889 generated flows) is now complete. Across 354,199 unique direct matches, first-packet counts plus the expanded legacy-order-informed aggregate flag mapping reached 88.14% feature-cell agreement and 266,769 exact 67-feature rows; the same first-packet extraction with the active mapping reached 86.31% and 105,893 exact rows. Direct-match coverage remains uneven: PortScan 99.90%, DDoS 31.38%, Bot 40.84%. Detector quality did not materially improve: RF recall/FPR were 20.32%/0.48% for the candidate versus 20.29%/0.48% baseline; IF recall/FPR were 11.27%/0.79% versus 15.06%/1.03%. This is same-benchmark evidence, not external validation. Both reports are datasets/reference_pcaps/friday-reference/Friday-attack-windows-first-packet-flags-legacy-order-candidate-evaluation.json and ...-baseline-evaluation.json. The mapping remains evaluation-only; production extraction and API behavior are unchanged.

The reviewed upstream source contains a legacy exporter that iterates a Java HashMap for flag values and an extended exporter that writes flags in explicit order; the current upstream flow writer calls the extended exporter. The candidate is consistent with the legacy order on this sample, but the exact version and export path used for CICIDS2017 are still unknown. This remains evaluation-only: no production feature mapping or active model changed, and parity is not certified. Relevant source: [BasicFlow.java](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/BasicFlow.java), [FlowGenerator.java](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/FlowGenerator.java), and [FlowFeature.java](https://github.com/ahlashkari/CICFlowMeter/blob/master/src/main/java/cic/cs/unb/ca/jnetpcap/FlowFeature.java).


## Training runtime notes

On the Ubuntu host, the Random Forest and Isolation Forest training scripts already set n_jobs=-1 and can use all 28 logical CPU threads. Hybrid V2 uses 100 Random Forest trees and 300 Isolation Forest trees. Original production training-duration logs are unavailable; a controlled same-host RF fit-only comparison is recorded below.

The Hybrid V2 and Friday-evaluation preparation scripts are identical apart from their output directory. Their saved preprocessor and feature list have matching SHA-256 hashes. I restored the 13 prepared arrays (about 715 MiB) into datasets/processed/hybrid_v2_training, so the RF trainer can reuse its cache and skip another full Parquet preparation pass. The normal-only Isolation Forest arrays have now also been prepared under datasets/processed/anomaly_training: 200,000 training rows, 431,276 Thursday-normal calibration rows, and 703,245 Friday rows. The active models and thresholds remain unchanged. Reducing tree counts or sample sizes changes the trained model and requires its own validation and threshold calibration.

### Half-tree Random Forest candidate (2026-11-12)

A separate 50-tree candidate was trained on the same 300,000-row, 67-feature Hybrid V2 training arrays, using the active model's depth, leaf size, class weighting, and random seed. A same-host fit-only benchmark took 10.228 seconds for 100 trees and 5.286 seconds for 50 trees, a 48.3% reduction in Random Forest fit time. The candidate artifact is 794,881 bytes versus 1,558,918 bytes for the active 100-tree model (49.0% smaller). This measures only RF fitting with prepared arrays; it does not halve end-to-end project time, which also includes data preparation, packet extraction, and other model work.

The candidate threshold (0.25556) was selected on Thursday validation data, matching the existing threshold-selection procedure. Thursday F1 was 0.7906 versus 0.7915 for the active model at its threshold of 0.27. A one-pass Friday holdout evaluation with those thresholds produced F1 0.4460 versus 0.4462, recall 28.83% versus 28.84%, and false-positive rates 0.312% versus 0.292%. Ranking quality was lower for the candidate (ROC-AUC 0.7590 versus 0.8275; PR-AUC 0.7290 versus 0.7971). Both models detected no Bot flows; DDoS and PortScan recall stayed near the active model's already limited levels. The candidate remains isolated and is not served by the API. Its training, Thursday calibration, Friday metrics, and per-family metrics are under `datasets/processed/candidate_results/rf-50-tree-20261112T031525Z/`; its weights are under `saved_models/candidates/rf-50-tree-20261112T031525Z/`. The candidate scripts are `app/detection/train_rf_half_tree_candidate.py`, `app/detection/evaluate_rf_half_tree_candidate.py`, and `app/detection/benchmark_rf100_fit.py`. This same-benchmark evaluation is not external validation; research use only, with no automated blocking or alert escalation.

### Half-tree Isolation Forest candidate (2026-11-12)

A separate 150-tree Isolation Forest was trained on 200,000 normal-only rows. Its Thursday threshold was set to the 99th percentile of Thursday normal scores (1% target false-positive rate), then frozen before the Friday evaluation. Fit time was 1.021 seconds versus 1.994 seconds for a same-data 300-tree fit (48.8% lower); the candidate file is 1,306,788 bytes versus 2,641,482 bytes for the active model (50.5% smaller).

On Friday, the candidate reached 20.55% recall, 73.46% precision, 0.3212 F1, 5.18% FPR, and 0.7019 ROC-AUC. The active model scored 19.64% recall, 72.77% precision, 0.3093 F1, 5.13% FPR, and 0.7112 ROC-AUC at its stored threshold. The candidate detected 59,253/128,027 DDoS flows, 83/158,930 PortScan flows, and 44/1,966 Bot flows. These differences are small and mixed; the two models remain experimental. Candidate weights and metrics are under `saved_models/candidates/if-150-tree-20261112T032703Z/` and `datasets/processed/candidate_results/if-150-tree-20261112T032703Z/`. The repeatable candidate script is `app/detection/train_if_half_tree_candidate.py`. It does not modify the active model or API. This same-benchmark evaluation is not external validation; do not use it for automated blocking or alert escalation.

## Capture-day holdout evaluation

The project now also has a capture-day-disjoint Random Forest evaluation. It trains a separate model on up to 300,000 flows from Monday through Thursday and evaluates on 703,243 Friday flows after removing ambiguous and cross-day duplicate feature patterns. The eight per-day flow Parquets were downloaded from an unofficial Hugging Face mirror and checked against the SHA-256 values listed for each file. The combined day-tagged dataset contains 2,830,743 flows, matching the row count of the existing processed dataset.

The primary Hybrid V2 models used by `/api/v1/detect/v2` were evaluated separately with Monday-Wednesday training, Thursday threshold selection, and Friday testing. The Friday test retained 702,164 flows after conflict and cross-day overlap filtering. At the frozen thresholds, Random Forest recall was 28.84% (FPR 0.29%); Isolation Forest recall was 19.71% (FPR 5.13%). The API continues to return each detector's signal separately. An offline OR combination reached 28.88% recall with 5.42% FPR, while AND reached 19.67% recall with a 0.001% FPR. These comparisons do not change the active model artifacts or thresholds. On Friday, Random Forest detected 64.42% of DDoS, 0.35% of PortScan, and 0% of Bot flows.

At the default 0.5 threshold, the separate baseline Friday holdout scored 70.46% accuracy, 99.65% precision, 28.19% recall, 0.4395 F1, 0.8042 ROC-AUC, and 0.07% false-positive rate. Detection by Friday attack family was 63.39% for DDoS, 0.19% for PortScan, and 0% for Bot. PortScan and Bot are present only in Friday's held-out flows, so their results expose poor generalization to attack families absent from the training days. Even at a threshold selected to keep the false-positive rate under 1%, recall was only 39.08%.

This is an evaluation-only model; it did not replace the weights served by the API. It evaluates derived flow tables from the same CICIDS2017 benchmark, not a raw PCAP replay through the live packet adapter or traffic from an external network. Feature parity with the exact CICFlowMeter training build remains unresolved. Do not use the result for automatic blocking or alert escalation.

The baseline metrics and threshold sweep are saved at `datasets/processed/day_based_results/capture_day_holdout_evaluation.json` and `datasets/processed/day_based_results/capture_day_holdout_threshold_sweep.csv`. The primary Hybrid V2 report is `datasets/processed/hybrid_v2_friday_holdout_results/hybrid_v2_friday_holdout_summary.json`; detailed CSVs and predictions are in that directory. To regenerate the isolated Hybrid V2 evaluation after the day-tagged dataset exists, run `app.preprocessing.prepare_hybrid_v2_friday_eval`, `app.detection.transform_hybrid_v2_friday_eval`, then `app.detection.evaluate_hybrid_v2_friday_eval`. These commands write evaluation arrays and reports outside the active model directories. The readiness endpoint reports these results after the API is restarted to load the updated code.

