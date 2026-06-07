"""
post_value_score.py
===================
Core scoring engine for the Marketing Content Optimization System.

Computes a composite Value Score (0–100) for each news post using
four marketing metrics, each percentile-ranked against the full dataset:

    Metric                        Weight
    ─────────────────────────────────────
    view_count                     30 %
    seo_linkdex                    25 %
    seo_content_score              25 %
    estimated_reading_time_minutes 20 %

Reading time is scored against an ideal engagement band (2–4 min)
rather than raw percentile, since more is not always better.

Topic categories are inferred from title patterns because the raw
data only contains a single "post" category.
"""

import re
import pandas as pd
import numpy as np

# ── Scoring weights (must sum to 1.0) ─────────────────────────────────────
WEIGHTS = {
    "view_count":                      0.30,
    "seo_linkdex":                     0.25,
    "seo_content_score":               0.25,
    "estimated_reading_time_minutes":  0.20,
}

# ── Ideal reading-time band ────────────────────────────────────────────────
IDEAL_READ_MIN = 2   # minutes
IDEAL_READ_MAX = 4   # minutes

# ── Topic category keyword rules (evaluated in order, first match wins) ────
TOPIC_RULES = [
    ("Trainer Spotlight",      [r"trainer spotlight"]),
    ("Health & Wellness",      [r"health benefit", r"wellness", r"seminar", r"morning tea", r"hydrotherapy swim"]),
    ("Aquatics & Swim School", [r"swim school", r"aqua aerobic", r"aquatic", r"hydrotherapy", r"lane availability", r"pool maintenance", r"swimming carnival"]),
    ("Group Fitness",          [r"why you should add", r"group fitness", r"zumba", r"pilates", r"bodypump", r"hiit", r"spin", r"yoga", r"senior functional"]),
    ("Facility Operations",    [r"opening hours", r"closure", r"maintenance", r"timetable update", r"schedule", r"public holiday"]),
    ("Equipment Upgrades",     [r"new upgrade", r"arriving soon"]),
    ("Programs & Enrolments",  [r"enrolment", r"school holiday", r"bookings open", r"term \d"]),
]


def infer_topic(title: str) -> str:
    """Return the best-matching topic category for a post title."""
    t = title.lower()
    for category, patterns in TOPIC_RULES:
        if any(re.search(p, t) for p in patterns):
            return category
    return "General"


def reading_time_score(minutes: float) -> float:
    """
    Score reading time 0–100.
    Full marks inside the ideal band; linear penalty outside it.
    """
    if IDEAL_READ_MIN <= minutes <= IDEAL_READ_MAX:
        return 100.0
    if minutes < IDEAL_READ_MIN:
        return max(0.0, 100.0 - (IDEAL_READ_MIN - minutes) * 35)
    # minutes > IDEAL_READ_MAX
    return max(0.0, 100.0 - (minutes - IDEAL_READ_MAX) * 20)


def percentile_scale(series: pd.Series) -> pd.Series:
    """Convert a numeric series to 0–100 percentile ranks."""
    return series.rank(pct=True) * 100


def compute_value_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Accept the raw posts DataFrame.
    Returns a copy with these extra columns:

        topic_category      – inferred content pillar
        pct_views           – percentile rank of view_count
        pct_seo_linkdex     – percentile rank of seo_linkdex
        pct_seo_content     – percentile rank of seo_content_score
        score_reading_time  – reading-time band score (0–100)
        value_score         – composite score (0–100, 1 dp)
        value_tier          – Gold / Silver / Bronze / Needs Work
        flag_undervalued    – True: high SEO, low views (hidden gem)
        flag_overexposed    – True: high views, low SEO (SEO risk)
    """
    d = df.copy()

    # Infer topic
    d["topic_category"] = d["title"].apply(infer_topic)

    # Per-metric scores
    d["pct_views"]          = percentile_scale(d["view_count"])
    d["pct_seo_linkdex"]    = percentile_scale(d["seo_linkdex"])
    d["pct_seo_content"]    = percentile_scale(d["seo_content_score"])
    d["score_reading_time"] = d["estimated_reading_time_minutes"].apply(reading_time_score)

    # Composite value score
    d["value_score"] = (
        d["pct_views"]          * WEIGHTS["view_count"]
        + d["pct_seo_linkdex"]  * WEIGHTS["seo_linkdex"]
        + d["pct_seo_content"]  * WEIGHTS["seo_content_score"]
        + d["score_reading_time"] * WEIGHTS["estimated_reading_time_minutes"]
    ).round(1)

    # Tier labels
    d["value_tier"] = pd.cut(
        d["value_score"],
        bins=[0, 40, 60, 80, 100],
        labels=["Needs Work", "Bronze", "Silver", "Gold"],
        include_lowest=True,
    ).astype(str)

    # Opportunity flags
    seo_avg = (d["seo_linkdex"] + d["seo_content_score"]) / 2
    view_med = d["view_count"].median()
    seo_med  = seo_avg.median()

    d["flag_undervalued"] = (seo_avg > seo_med) & (d["view_count"] < view_med)
    d["flag_overexposed"] = (d["view_count"] > view_med) & (seo_avg < seo_med)

    return d


# ── Quick CLI smoke-test ───────────────────────────────────────────────────
if __name__ == "__main__":
    from pathlib import Path
    path = Path(__file__).parent.parent / "data" / "facility_news_posts_export.csv"
    df = compute_value_scores(pd.read_csv(path))

    cols = ["title", "topic_category", "value_score", "value_tier",
            "view_count", "seo_linkdex", "seo_content_score",
            "estimated_reading_time_minutes"]

    print("\n── Top 10 by Value Score ──")
    print(df.nlargest(10, "value_score")[cols].to_string(index=False))

    print("\n── Undervalued (high SEO, low views) ──")
    print(df[df["flag_undervalued"]][cols].head(5).to_string(index=False))

    print("\n── Overexposed (high views, low SEO) ──")
    print(df[df["flag_overexposed"]][cols].head(5).to_string(index=False))

    print("\n── Value score distribution ──")
    print(df["value_tier"].value_counts().to_string())
