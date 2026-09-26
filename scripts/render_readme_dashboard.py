"""Render a deterministic README preview from real pipeline outputs."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs" / "real" / "reports"
MARTS = ROOT / "outputs" / "real" / "marts"
TARGET = ROOT / "docs" / "assets" / "uci-dashboard-overview.jpg"


def card(fig, xywh, title, value, note):
    x, y, w, h = xywh
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
                       transform=fig.transFigure, facecolor="white", edgecolor="#dce5e1", linewidth=1))
    fig.text(x + .018, y + h - .036, title, color="#60747a", fontsize=10)
    fig.text(x + .018, y + .046, value, color="#102f3a", fontsize=22, weight="bold")
    fig.text(x + .018, y + .017, note, color="#60747a", fontsize=8)


def main():
    metrics = json.loads((REPORTS / "metrics.json").read_text(encoding="utf-8"))
    quality = json.loads((REPORTS / "data_quality.json").read_text(encoding="utf-8"))
    fact = pd.read_csv(MARTS / "fact_sales.csv", parse_dates=["event_date"])
    scores = pd.read_csv(MARTS / "customer_scores.csv")
    monthly = fact.groupby(fact.event_date.dt.to_period("M")).net_revenue.sum()
    segments = scores.segment.value_counts().sort_values()
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})
    fig = plt.figure(figsize=(16, 9), dpi=120, facecolor="#f5f6f2")
    fig.patches.append(FancyBboxPatch((0, .89), 1, .11, boxstyle="square,pad=0", transform=fig.transFigure,
                                     facecolor="#102f3a", edgecolor="#102f3a"))
    fig.text(.045, .937, "Retail", color="white", fontsize=22, weight="bold", va="center")
    fig.text(.107, .937, "Scope", color="#f4a181", fontsize=22, weight="bold", va="center")
    fig.text(.955, .937, "UCI REAL DATA · v0.2", color="#c5d8d6", fontsize=9, ha="right", va="center")
    fig.text(.045, .845, "Gerçek işlemlerden ölçülebilir müşteri içgörüsü", color="#102f3a", fontsize=24, weight="bold")
    fig.text(.045, .813, "Zaman temelli segmentasyon, 90 günlük inaktivite riski ve gelir tahmini · GBP", color="#60747a", fontsize=10)
    widths = [.205] * 4
    starts = [.045, .278, .511, .744]
    values = [f"{quality['known_customers']:,}", f"{len(scores):,}", f"£{fact.net_revenue.sum()/1_000_000:.2f}M",
              f"{quality['sale_orders']:,}"]
    titles = ["Tanımlı müşteri", "Skorlanan müşteri", "Net gelir", "Satış siparişi"]
    notes = ["Kimliği bulunan kayıtlar", "Son 180 günde alışveriş", "İadeler düşülmüş", "Benzersiz fatura"]
    for x, w, t, v, n in zip(starts, widths, titles, values, notes):
        card(fig, (x, .68, w, .105), t, v, n)
    ax1 = fig.add_axes([.055, .31, .57, .30], facecolor="white")
    ax1.plot(range(len(monthly)), monthly.values / 1000, color="#197b73", linewidth=2.4)
    ax1.fill_between(range(len(monthly)), monthly.values / 1000, color="#197b73", alpha=.08)
    ticks = list(range(0, len(monthly), 4))
    if len(monthly) - 1 not in ticks:
        ticks.append(len(monthly) - 1)
    ax1.set_xticks(ticks, [str(monthly.index[i]) for i in ticks], fontsize=8)
    ax1.set_ylabel("GBP (thousand)", fontsize=9, color="#60747a")
    ax1.set_title("Monthly net revenue", loc="left", fontsize=13, color="#102f3a", pad=12)
    ax1.grid(axis="y", color="#e7ece9"); ax1.spines[:].set_visible(False); ax1.tick_params(colors="#60747a")
    ax2 = fig.add_axes([.675, .31, .27, .30], facecolor="white")
    ax2.barh(segments.index, segments.values, color="#197b73")
    ax2.set_title("Current customer segments", loc="left", fontsize=13, color="#102f3a", pad=12)
    ax2.grid(axis="x", color="#e7ece9"); ax2.set_axisbelow(True); ax2.spines[:].set_visible(False); ax2.tick_params(labelsize=8, colors="#60747a")
    c = metrics["test_classification"]
    fig.text(.055, .245, "Held-out test", fontsize=11, weight="bold", color="#102f3a")
    fig.text(.055, .205, f"AP  {c['average_precision']:.3f}", fontsize=17, weight="bold", color="#102f3a")
    fig.text(.18, .205, f"ROC-AUC  {c['roc_auc']:.3f}", fontsize=17, weight="bold", color="#102f3a")
    fig.text(.37, .205, f"Top-20% lift  {c['lift_at_20pct']:.2f}×", fontsize=17, weight="bold", color="#102f3a")
    fig.text(.62, .205, f"Revenue MAE  £{metrics['test_value']['mae']:.0f}", fontsize=17, weight="bold", color="#102f3a")
    fig.text(.055, .158, "Chronological split · 2,772 test customers · model selected on validation only", fontsize=9, color="#60747a")
    fig.text(.055, .08, "Source: UCI Online Retail II (CC BY 4.0). No cost, consent or contact data; scores are not activation-ready.", fontsize=9, color="#60747a")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(TARGET, bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=80,
                format="jpg", pil_kwargs={"quality": 88, "optimize": True})
    print(TARGET)


if __name__ == "__main__":
    main()
