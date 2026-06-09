"""
analyse_opportunities.py
=========================
Analyses scored posts for content opportunities and writes opportunities.json.

Computes:
  - Undervalued posts  : high SEO, low views — worth promoting
  - Overexposed posts  : high views, low SEO — SEO needs fixing
  - Topic gaps         : categories below overall average value score
  - Seasonal gaps      : months with below-average post volume

Run after build_benchmarks.py.

Usage:
    python3 scoring/analyse_opportunities.py

Output:
    data/opportunities.json
"""

import json
import sys
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from post_value_score import compute_value_scores

DATA_PATH   = Path(__file__).parent.parent / "data" / "facility_news_posts_export.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "opportunities.json"

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def r(val, dp=1):
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(val), dp)


def post_row(row, action):
    return {
        "title":          row["title"],
        "topic_category": row["topic_category"],
        "value_score":    r(row["value_score"]),
        "views":          int(row["view_count"]),
        "seo_linkdex":    int(row["seo_linkdex"]),
        "seo_content":    int(row["seo_content_score"]),
        "action":         action,
    }


def compute_seasonal_gaps(df: pd.DataFrame) -> dict:
    df = df.copy()
    df["month_num"]  = pd.to_datetime(df["post_date"]).dt.month
    df["month_name"] = pd.to_datetime(df["post_date"]).dt.strftime("%B")
    counts = df.groupby(["month_num", "month_name"]).size().reset_index(name="count")
    avg    = counts["count"].mean()
    gaps   = counts[counts["count"] < avg * 0.80].sort_values("month_num")
    return {
        row["month_name"]: {
            "posts":      int(row["count"]),
            "avg":        round(avg, 1),
            "suggestion": "Content volume below average — plan 1–2 extra posts this month.",
        }
        for _, row in gaps.iterrows()
    }


def compute_topic_gaps(df: pd.DataFrame) -> dict:
    cat_avg    = df.groupby("topic_category")["value_score"].mean().round(1)
    global_avg = cat_avg.mean()
    return {
        cat: {
            "avg_value_score": float(score),
            "vs_overall":      round(float(score) - global_avg, 1),
            "suggestion":      "Below-average pillar — review SEO quality and content depth.",
        }
        for cat, score in cat_avg.items() if score < global_avg
    }


def analyse():
    print(f"Loading {DATA_PATH} …")
    raw = pd.read_csv(DATA_PATH)
    df  = compute_value_scores(raw)
    print(f"Analysing {len(df)} posts …")

    # Undervalued and overexposed posts
    undervalued = df[df["flag_undervalued"]].nlargest(10, "value_score")
    overexposed = df[df["flag_overexposed"]].nlargest(10, "view_count")

    # Topic and seasonal gaps
    topic_gaps    = compute_topic_gaps(df)
    seasonal_gaps = compute_seasonal_gaps(df)
    global_avg    = df["value_score"].mean()

    out = {
        "_meta": {
            "generated":   pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "source":      "facility_news_posts_export.csv",
            "total_posts": len(df),
        },
        "undervalued": [
            post_row(row, "High SEO strength but low visibility — push via social or internal linking.")
            for _, row in undervalued.iterrows()
        ],
        "overexposed": [
            post_row(row, "Getting traffic but weak SEO — optimise meta, headings & keyword use.")
            for _, row in overexposed.iterrows()
        ],
        "gap_analysis": {
            "overall_avg_value_score": r(global_avg),
            "underperforming_topics":  topic_gaps,
            "seasonal_gaps":           seasonal_gaps,
        },
    }

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n✅  opportunities.json written → {OUTPUT_PATH}")
    print(f"    Undervalued posts       : {len(out['undervalued'])}")
    print(f"    Overexposed posts       : {len(out['overexposed'])}")
    print(f"    Underperforming topics  : {', '.join(topic_gaps.keys())}")
    print(f"    Seasonal gaps           : {', '.join(seasonal_gaps.keys()) or 'none'}")


if __name__ == "__main__":
    analyse()
