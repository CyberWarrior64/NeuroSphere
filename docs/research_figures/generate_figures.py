"""Generate publication-ready NeuroSphere result figures from checked-in results."""
from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SCALE = 1.5  # 8 x 5 in at 300 dpi for the 1600 x 1000 figures.
W, H = 1600, 1000
INK = "#183247"
MUTED = "#536879"
GRID = "#DCE5EC"
AXIS = "#9BAFBD"
BLUE = "#2878B5"
ORANGE = "#E68A35"
TEAL = "#239B8E"
PURPLE = "#7963B6"
PALE = "#F3F7FA"
WHITE = "#FFFFFF"
FONT_PATH = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\arialbd.ttf")


class Figure:
    def __init__(self, width=W, height=H):
        self.width, self.height = width, height
        self.ops: list[str] = []
        self.img = Image.new("RGB", (round(width * SCALE), round(height * SCALE)), WHITE)
        self.draw = ImageDraw.Draw(self.img)
        self.ops.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="8in" height="5in" viewBox="0 0 {width} {height}">')
        self.ops.append('<rect width="100%" height="100%" fill="#fff"/>')

    def rect(self, x, y, w, h, fill, stroke="none", sw=1):
        self.ops.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        self.draw.rectangle((round(x*SCALE), round(y*SCALE), round((x+w)*SCALE), round((y+h)*SCALE)), fill=fill, outline=None if stroke == "none" else stroke, width=max(1, round(sw*SCALE)))

    def line(self, x1, y1, x2, y2, color=GRID, sw=2):
        self.ops.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"/>')
        self.draw.line((round(x1*SCALE), round(y1*SCALE), round(x2*SCALE), round(y2*SCALE)), fill=color, width=max(1, round(sw*SCALE)))

    def text(self, x, y, value, size=26, color=INK, bold=False, anchor="start"):
        family = "Arial"
        weight = "700" if bold else "400"
        safe = html.escape(str(value))
        text_anchor = {"start": "start", "middle": "middle", "end": "end"}[anchor]
        self.ops.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="{family},sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{text_anchor}" dominant-baseline="middle">{safe}</text>')
        font_path = FONT_BOLD_PATH if bold else FONT_PATH
        font = ImageFont.truetype(str(font_path), round(size*SCALE))
        pil_anchor = {"start": "lm", "middle": "mm", "end": "rm"}[anchor]
        self.draw.text((round(x*SCALE), round(y*SCALE)), str(value), fill=color, font=font, anchor=pil_anchor)

    def title(self, heading, subtitle):
        self.text(90, 70, heading, 42, INK, True)
        self.text(90, 125, subtitle, 23, MUTED)
        self.line(90, 166, self.width-90, 166, GRID, 2)

    def legend_item(self, x, y, color, label, size=21):
        self.rect(x, y-11, 24, 22, color)
        self.text(x+36, y, label, size, MUTED)

    def save(self, name):
        self.ops.append("</svg>")
        (OUT / f"{name}.svg").write_text("\n".join(self.ops), encoding="utf-8")
        self.img.save(OUT / f"{name}.png", dpi=(300, 300), optimize=True)


def load_results():
    random = json.loads((ROOT / "ai-engine/datasets/processed/validated_randomsplit_results/evaluation.json").read_text(encoding="utf-8"))
    holdout = json.loads((ROOT / "ai-engine/datasets/processed/hybrid_v2_friday_holdout_results/hybrid_v2_friday_holdout_summary.json").read_text(encoding="utf-8"))
    readme = (ROOT / "ai-engine/README.md").read_text(encoding="utf-8")
    match = re.search(
        r"found ([\d.]+)% feature-cell agreement across ([\d,]+) unique direct flows; ([\d,]+) flows matched all 67 fields\..*?Among the ([\d,]+) flows with exact core duration/count/payload fields, ([\d.]+)% of feature cells matched and ([\d.]+)% matched all 67 fields",
        readme,
        re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find the documented first-100,000-packet parity summary in ai-engine/README.md")
    parity = {
        "cell_all": float(match.group(1)),
        "matched_all": int(match.group(2).replace(",", "")),
        "complete_all": int(match.group(3).replace(",", "")),
        "matched_core": int(match.group(4).replace(",", "")),
        "cell_core": float(match.group(5)),
        "complete_core_pct": float(match.group(6)),
    }
    parity["complete_all_pct"] = 100 * parity["complete_all"] / parity["matched_all"]
    return random, holdout, parity


def plot_grouped(f, groups, colors, metrics, x0, x1, y0, y1, labels, max_value=100, tick_step=20, bar_width=50, group_gap=80, value_fmt=lambda x: f"{x:.1f}%"):
    plot_h = y1-y0
    for tick in range(0, max_value+1, tick_step):
        y = y1 - plot_h*tick/max_value
        f.line(x0, y, x1, y, GRID, 2 if tick else 3)
        f.text(x0-18, y, f"{tick}%", 19, MUTED, anchor="end")
    count = len(groups)
    centers = [x0 + (x1-x0)*(i+0.5)/count for i in range(count)]
    bar_gap = 10
    total = len(labels)*bar_width + (len(labels)-1)*bar_gap
    for center, (group_name, values) in zip(centers, groups):
        start = center-total/2
        for i, label in enumerate(labels):
            value = values[i]
            h = plot_h*value/max_value
            x = start+i*(bar_width+bar_gap)
            y = y1-h
            f.rect(x, y, bar_width, h, colors[label])
            f.text(x+bar_width/2, max(y-22, y0-10), value_fmt(value), 17, INK, True, "middle")
        f.text(center, y1+42, group_name, 21, INK, True, "middle")


def random_split_figure(random):
    f = Figure()
    f.title("Model performance on a stratified random split", "Filtered CICIDS2017 flow table · binary attack class · random split is not capture-day-disjoint")
    metrics = ["precision", "recall", "f1"]
    models = {"Random Forest": (random["rf"], BLUE), "Isolation Forest": (random["isolation_forest"], ORANGE)}
    group_data = []
    for metric in metrics:
        group_data.append((metric.title(), [100*model[metric] for model, _ in models.values()]))
    colors = {name: col for name, (_, col) in models.items()}
    for i, name in enumerate(models):
        f.legend_item(540+i*260, 202, colors[name], name, 21)
    plot_grouped(f, group_data, colors, metrics, 180, 1430, 300, 700, list(models), bar_width=135, group_gap=80, value_fmt=lambda x: f"{x:.1f}%")
    f.text(90, 790, "False-positive rate", 21, MUTED, True)
    f.text(345, 790, f"Random Forest  {100*random['rf']['false_positive_rate']:.2f}%", 21, BLUE, True)
    f.text(810, 790, f"Isolation Forest  {100*random['isolation_forest']['false_positive_rate']:.2f}%", 21, ORANGE, True)
    f.rect(90, 845, 1420, 88, PALE)
    f.text(115, 875, f"Test n = {random['split_rows']['test']:,}  ·  Filtered total n = {random['rows_after_filtering']:,}  ·  Stratified 60/20/20 split", 20, MUTED)
    f.text(115, 909, "Conflict patterns and exact feature duplicates removed; this split does not test generalization to unseen capture days.", 18, MUTED)
    f.save("figure_1_random_split_metrics")


def holdout_figure(holdout):
    f = Figure(1900, 1150)
    # Override output dimensions to an 9.5 x 5.75 in vector canvas and 300 dpi raster.
    # Figure.__init__ defaults are suitable for panels; use the actual size for both formats.
    f.title("Model performance on the Friday capture-day holdout", "Thresholds were frozen before Friday · trained Monday–Wednesday · calibrated Thursday · experimental evaluation")
    models = [(m["Detector"], m) for m in holdout["metrics"]]
    palette = {"Random Forest V2": BLUE, "Isolation Forest V2": ORANGE, "Hybrid OR": TEAL, "Hybrid AND": PURPLE}
    labels = [name for name, _ in models]
    metrics = ["Precision", "Recall", "F1"]
    group_data = [(metric, [100*m[metric] for _, m in models]) for metric in metrics]
    colors = {name: palette[name] for name in labels}
    for i, name in enumerate(labels):
        f.legend_item(180+i*360, 205, colors[name], name, 18)
    plot_grouped(f, group_data, colors, metrics, 130, 1120, 300, 850, labels, bar_width=54, group_gap=70, value_fmt=lambda x: f"{x:.1f}%")
    # False-positive rate panel uses its own explicit 0–6% scale.
    f.text(1265, 260, "False-positive rate", 26, INK, True)
    f.text(1265, 300, "0–6% scale", 18, MUTED)
    px0, px1, py0, py1 = 1400, 1810, 375, 815
    for tick in range(0, 7, 1):
        x = px0+(px1-px0)*tick/6
        f.line(x, py0, x, py1, GRID, 2)
        f.text(x, py1+30, f"{tick}%", 17, MUTED, anchor="middle")
    row_y = [405, 505, 605, 705]
    for (name, metric), y in zip(models, row_y):
        f.text(1265, y, name, 18, INK)
        val = 100*metric["FPR"]
        barw = (px1-px0)*val/6
        if val > 0:
            f.rect(px0, y+25, max(barw, 3), 27, palette[name])
        f.text(min(px0+barw+12, px1), y+38, f"{val:.3f}%" if val < .01 else f"{val:.2f}%", 18, INK, True)
    f.line(90, 920, 1810, 920, GRID, 2)
    f.text(100, 960, f"Friday test set n = {holdout['test_rows']:,} · same CICIDS2017 benchmark; not external-network validation.", 20, MUTED)
    f.text(100, 1000, "Hybrid OR/AND are offline combinations of detector signals; weak PortScan and Bot generalization remains a limitation.", 18, MUTED)
    f.ops[0] = f'<svg xmlns="http://www.w3.org/2000/svg" width="9.5in" height="5.75in" viewBox="0 0 {f.width} {f.height}">'
    f.img.save(OUT / "figure_2_friday_holdout_metrics.png", dpi=(300, 300), optimize=True)
    f.ops.append("</svg>")
    (OUT / "figure_2_friday_holdout_metrics.svg").write_text("\n".join(f.ops), encoding="utf-8")


def parity_figure(parity):
    f = Figure()
    f.title("Packet feature agreement in a bounded CICIDS2017 comparison", "First 100,000 packets from Monday capture · 5,831 direct flow matches · agreement is not full-generator validation")
    f.legend_item(475, 205, BLUE, "Feature-cell agreement", 20)
    f.legend_item(860, 205, TEAL, "Complete 67-feature vectors", 20)
    groups = [
        ("All direct matches", [parity["cell_all"], parity["complete_all_pct"]]),
        ("Core-exact subset", [parity["cell_core"], parity["complete_core_pct"]]),
    ]
    colors = {"Feature-cell agreement": BLUE, "Complete 67-feature vectors": TEAL}
    plot_grouped(f, groups, colors, [], 220, 1380, 300, 700, list(colors), bar_width=190, group_gap=80, value_fmt=lambda x: f"{x:.2f}%" if x < 100 else "100%")
    f.text(480, 768, f"n = {parity['matched_all']:,} flows", 20, MUTED, anchor="middle")
    f.text(1120, 768, f"n = {parity['matched_core']:,} flows", 20, MUTED, anchor="middle")
    f.rect(90, 825, 1420, 108, PALE)
    f.text(115, 860, f"Complete vectors: {parity['complete_all']:,}/{parity['matched_all']:,} = {parity['complete_all_pct']:.2f}% overall; {parity['complete_all']:,}/{parity['matched_core']:,} = {parity['complete_core_pct']:.2f}% in core-exact subset.", 18, MUTED)
    f.text(115, 902, "Core-exact rows match duration, packet counts, and directional payload totals; subset agreement is conditional on that match.", 18, MUTED)
    f.save("figure_3_packet_feature_parity")


def write_sources(random, holdout, parity):
    with (OUT / "source_metrics.csv").open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["evaluation", "model_or_group", "metric", "value_percent", "denominator_n"])
        for name, key in [("Random split", "rf"), ("Random split", "isolation_forest")]:
            m = random[key]
            model = "Random Forest" if key == "rf" else "Isolation Forest"
            for metric in ("precision", "recall", "f1", "false_positive_rate"):
                writer.writerow([name, model, metric, 100*m[metric], random["split_rows"]["test"]])
        for m in holdout["metrics"]:
            for field in ("Precision", "Recall", "F1", "FPR"):
                writer.writerow(["Friday capture-day holdout", m["Detector"], field, 100*m[field], holdout["test_rows"]])
        parity_rows = [
            ("All direct matches", "Feature-cell agreement", parity["cell_all"], parity["matched_all"]),
            ("All direct matches", "Complete 67-feature vectors", parity["complete_all_pct"], parity["matched_all"]),
            ("Core-exact subset", "Feature-cell agreement", parity["cell_core"], parity["matched_core"]),
            ("Core-exact subset", "Complete 67-feature vectors", parity["complete_core_pct"], parity["matched_core"]),
        ]
        for group, metric, value, denominator in parity_rows:
            writer.writerow(["Feature parity", group, metric, value, denominator])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    random, holdout, parity = load_results()
    random_split_figure(random)
    holdout_figure(holdout)
    parity_figure(parity)
    write_sources(random, holdout, parity)
    print(f"Generated three figures in {OUT}")


if __name__ == "__main__":
    main()
