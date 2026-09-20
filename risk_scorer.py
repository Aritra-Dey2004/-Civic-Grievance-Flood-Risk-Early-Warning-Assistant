"""
Flood-risk scoring.

Combines two signals per ward:
  1. How many recent complaints were classified as Waterlogging/Drainage
     (crowdsourced signal from citizens).
  2. Recent rainfall (mm) in that ward (environmental signal).

Both are normalized to 0-1 and combined into a single risk score, so no
single signal dominates just because of its raw scale. The score is
deliberately simple and explainable (Responsible AI: transparency) rather
than a black-box model - every score shows exactly which numbers produced it.
"""

import pandas as pd

# How much weight each signal gets in the final score.
COMPLAINT_WEIGHT = 0.5
RAINFALL_WEIGHT = 0.5

RISK_THRESHOLDS = {
    "High": 0.66,
    "Medium": 0.33,
}


def _risk_level(score: float) -> str:
    if score >= RISK_THRESHOLDS["High"]:
        return "High"
    if score >= RISK_THRESHOLDS["Medium"]:
        return "Medium"
    return "Low"


def score_wards(classified_complaints_df: pd.DataFrame, rainfall_df: pd.DataFrame) -> pd.DataFrame:
    """
    classified_complaints_df must have columns: ward, is_flood_related
    rainfall_df must have columns: ward, rainfall_mm (multiple rows per ward OK)
    """
    flood_counts = (
        classified_complaints_df[classified_complaints_df["is_flood_related"]]
        .groupby("ward")
        .size()
        .rename("flood_complaint_count")
    )

    rainfall_recent = rainfall_df.groupby("ward")["rainfall_mm"].max().rename("recent_max_rainfall_mm")

    all_wards = sorted(set(rainfall_df["ward"]) | set(classified_complaints_df["ward"]))
    result = pd.DataFrame(index=all_wards)
    result.index.name = "ward"
    result = result.join(flood_counts).join(rainfall_recent).fillna(0)

    max_complaints = max(result["flood_complaint_count"].max(), 1)
    max_rainfall = max(result["recent_max_rainfall_mm"].max(), 1)

    result["complaint_signal"] = result["flood_complaint_count"] / max_complaints
    result["rainfall_signal"] = result["recent_max_rainfall_mm"] / max_rainfall

    result["risk_score"] = (
        COMPLAINT_WEIGHT * result["complaint_signal"] + RAINFALL_WEIGHT * result["rainfall_signal"]
    ).round(2)

    result["risk_level"] = result["risk_score"].apply(_risk_level)

    result["explanation"] = result.apply(
        lambda r: (
            f"{int(r['flood_complaint_count'])} flood-related complaint(s) reported, "
            f"recent peak rainfall of {r['recent_max_rainfall_mm']:.0f}mm."
        ),
        axis=1,
    )

    result = result.reset_index().sort_values("risk_score", ascending=False)
    return result[
        [
            "ward",
            "flood_complaint_count",
            "recent_max_rainfall_mm",
            "risk_score",
            "risk_level",
            "explanation",
        ]
    ]
