"""
build_benchmarks.py
===================
Reads the scored posts dataset and writes benchmarks.json.

Run once to generate the benchmark file, then re-run whenever
you refresh the underlying CSV with new posts.

Usage:
    python build_benchmarks.py

Output:
    benchmarks.json  (project root)
"""

import json
import re
import pandas as pd
import numpy as np
from pathlib import Path
from post_value_score import compute_value_scores

DATA_PATH   = Path(__file__).parent / "data" / "facility_news_posts_export.csv"
OUTPUT_PATH = Path(__file__).parent / "benchmarks.json"


# ── Helpers ────────────────────────────────────────────────────────────────

def r(val, dp=1):
    """Round a value; return None for NaN/NA."""
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(val), dp)


def strip_update(title: str) -> str:
    """Remove '- Update N' suffix from a title."""
    return re.sub(r"\s*-\s*Update\s*\d+$", "", title, flags=re.IGNORECASE).strip()


def detect_title_format(title: str) -> str:
    t = strip_update(title)
    if re.match(r"Why You Should", t, re.I):
        return "Why You Should Add [X] to Your Weekly Routine"
    if re.match(r"The (Surprising|Amazing|Real|Hidden|Key)", t, re.I):
        return "The [Adjective] Health Benefits of [X]"
    if re.match(r"Trainer Spotlight", t, re.I):
        return "Trainer Spotlight: Meet [Name]"
    if re.match(r"(Upcoming|Notice of)", t, re.I):
        return "Upcoming / Notice of [Operational Update]"
    if re.match(r"New Upgrade", t, re.I):
        return "New Upgrade: Brand New [Equipment] Arriving Soon!"
    if re.search(r"Enrolment|Booking|Open for Term", t, re.I):
        return "[Program] – Enrolments/Bookings Open"
    if re.search(r"Opening Hours|Schedule|Timetable", t, re.I):
        return "[Season/Event] Opening Hours / Schedule Update"
    if re.search(r"Public Holiday", t, re.I):
        return "Public Holiday Opening Hours – [Holiday Name]"
    if re.search(r"School Holiday", t, re.I):
        return "School Holiday [Program] – Bookings Open!"
    return "Custom format"


def top_title_formats(titles: pd.Series, n: int = 3) -> list:
    formats = titles.apply(detect_title_format)
    return formats.value_counts().head(n).index.tolist()


def seasonal_gaps(df_scored: pd.DataFrame) -> dict:
    df_scored = df_scored.copy()
    df_scored["month_num"]  = pd.to_datetime(df_scored["post_date"]).dt.month
    df_scored["month_name"] = pd.to_datetime(df_scored["post_date"]).dt.strftime("%B")
    counts = df_scored.groupby(["month_num", "month_name"]).size().reset_index(name="count")
    avg    = counts["count"].mean()
    gaps   = counts[counts["count"] < avg * 0.80].sort_values("month_num")
    return {
        row["month_name"]: {
            "posts": int(row["count"]),
            "avg":   round(avg, 1),
            "suggestion": "Content volume below average — plan 1–2 extra posts this month.",
        }
        for _, row in gaps.iterrows()
    }


# ── Main ───────────────────────────────────────────────────────────────────

def build():
    print(f"Loading  {DATA_PATH} …")
    raw = pd.read_csv(DATA_PATH)
    df  = compute_value_scores(raw)
    print(f"Scored {len(df)} posts across {df['topic_category'].nunique()} topic categories.")

    # ── Overall benchmarks ─────────────────────────────────────────────────
    overall = {
        "total_posts":  len(df),
        "date_range": {
            "from": str(raw["post_date"].min()),
            "to":   str(raw["post_date"].max()),
        },
        "value_score": {
            "mean":                   r(df["value_score"].mean()),
            "median":                 r(df["value_score"].median()),
            "p75":                    r(df["value_score"].quantile(0.75)),
            "p90":                    r(df["value_score"].quantile(0.90)),
            "min_to_publish":         r(df["value_score"].quantile(0.40)),
            "target_good":            60.0,
            "target_great":           80.0,
        },
        "view_count": {
            "mean":   r(df["view_count"].mean(), 0),
            "median": r(df["view_count"].median(), 0),
            "p75":    r(df["view_count"].quantile(0.75), 0),
            "p90":    r(df["view_count"].quantile(0.90), 0),
        },
        "seo_linkdex": {
            "mean":       r(df["seo_linkdex"].mean()),
            "median":     r(df["seo_linkdex"].median()),
            "target_min": r(df["seo_linkdex"].quantile(0.60)),
        },
        "seo_content_score": {
            "mean":       r(df["seo_content_score"].mean()),
            "median":     r(df["seo_content_score"].median()),
            "target_min": r(df["seo_content_score"].quantile(0.60)),
        },
        "reading_time_minutes": {
            "mean":      r(df["estimated_reading_time_minutes"].mean()),
            "ideal_min": 2,
            "ideal_max": 4,
        },
        "tier_counts": df["value_tier"].value_counts().to_dict(),
        "undervalued_count": int(df["flag_undervalued"].sum()),
        "overexposed_count": int(df["flag_overexposed"].sum()),
    }

    # ── Per-topic benchmarks + post brief templates ────────────────────────
    by_topic = {}
    for topic, grp in df.groupby("topic_category"):
        top5 = grp.copy()
        top5["base_title"] = top5["title"].str.replace(r"\s*-\s*Update\s*\d+$", "", regex=True).str.strip()
        top5 = top5.sort_values("value_score", ascending=False).drop_duplicates("base_title").head(5)
        by_topic[topic] = {
            "post_count":          len(grp),
            "avg_value_score":     r(grp["value_score"].mean()),
            "avg_views":           r(grp["view_count"].mean(), 0),
            "avg_seo_linkdex":     r(grp["seo_linkdex"].mean()),
            "avg_seo_content":     r(grp["seo_content_score"].mean()),
            # Post brief template
            "brief_template": {
                "ideal_reading_time": {
                    "min": int(grp["estimated_reading_time_minutes"].quantile(0.25)),
                    "max": int(grp["estimated_reading_time_minutes"].quantile(0.75)),
                },
                "target_seo_linkdex":    r(grp["seo_linkdex"].quantile(0.70)),
                "target_seo_content":    r(grp["seo_content_score"].quantile(0.70)),
                "min_value_score_before_publish": r(grp["value_score"].quantile(0.40)),
                "winning_title_formats": top_title_formats(top5["title"]),
            },
            "top_posts": [
                {
                    "title":       row["title"],
                    "value_score": r(row["value_score"]),
                    "views":       int(row["view_count"]),
                    "seo_linkdex": int(row["seo_linkdex"]),
                    "seo_content": int(row["seo_content_score"]),
                    "read_mins":   int(row["estimated_reading_time_minutes"]),
                }
                for _, row in top5.iterrows()
            ],
        }

    # ── Opportunity lists ──────────────────────────────────────────────────
    undervalued = df[df["flag_undervalued"]].nlargest(10, "value_score")
    overexposed = df[df["flag_overexposed"]].nlargest(10, "view_count")

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

    opportunities = {
        "undervalued": [
            post_row(row, "High SEO strength but low visibility — push via social or internal linking.")
            for _, row in undervalued.iterrows()
        ],
        "overexposed": [
            post_row(row, "Getting traffic but weak SEO — optimise meta, headings & keyword use to lock in organic growth.")
            for _, row in overexposed.iterrows()
        ],
    }

    # ── Gap analysis ───────────────────────────────────────────────────────
    # Topic gaps: categories below overall average value score
    cat_avg     = df.groupby("topic_category")["value_score"].mean().round(1)
    global_avg  = cat_avg.mean()
    topic_gaps  = {
        cat: {
            "avg_value_score": float(score),
            "vs_overall":      round(float(score) - global_avg, 1),
            "suggestion":      "Below-average pillar — review SEO quality and content depth for this category.",
        }
        for cat, score in cat_avg.items() if score < global_avg
    }

    gap_analysis = {
        "overall_avg_value_score": r(global_avg),
        "underperforming_topics":  topic_gaps,
        "seasonal_gaps":           seasonal_gaps(df),
    }

    # ── Guidance rules (used by HTML checker) ─────────────────────────────
    guidance = {
        "tiers": {
            "Gold":        "Top performer — study this post's formula and replicate it.",
            "Silver":      "Solid. Small SEO or promotion improvements could push it to Gold.",
            "Bronze":      "Needs work. Improve SEO scores or expand thin content.",
            "Needs Work":  "Underperformer. Prioritise SEO fixes or reconsider the topic angle.",
        },
        "reading_time": {
            "too_short":   "Under 2 min feels thin — add practical tips, examples, or an FAQ.",
            "ideal":       "2–4 min is the engagement sweet spot for this site.",
            "too_long":    "Over 4 min for a news post may reduce completion rate — consider splitting into a series.",
        },
        "seo_linkdex": {
            "poor":    {"range": "0–44",  "tip": "Focus keyword barely present — use it in the title, H2s, and opening paragraph."},
            "fair":    {"range": "45–63", "tip": "Keyword usage is partial — strengthen meta description and add internal links."},
            "good":    {"range": "64–81", "tip": "Good keyword integration. Check image alt text and URL slug."},
            "strong":  {"range": "82–90", "tip": "Excellent SEO authority. Focus energy on promotion and distribution."},
        },
        "seo_content": {
            "poor":    {"range": "0–59",  "tip": "Content quality low — improve readability, structure, and keyword density."},
            "fair":    {"range": "60–74", "tip": "Decent content. Add subheadings, bullet points, or a clear CTA."},
            "good":    {"range": "75–89", "tip": "Strong content. Minor polish on transitions and CTAs will lift it further."},
            "strong":  {"range": "90",    "tip": "Maximum content score — this is the benchmark to write to."},
        },
    }

    # ── Assemble & write ───────────────────────────────────────────────────
    out = {
        "_meta": {
            "generated":     pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "source":        "facility_news_posts_export.csv",
            "total_posts":   len(df),
            "scoring_weights": {k: f"{int(v*100)}%" for k, v in {
                "view_count": 0.30, "seo_linkdex": 0.25,
                "seo_content_score": 0.25,
                "estimated_reading_time_minutes": 0.20,
            }.items()},
        },
        "overall":       overall,
        "by_topic":      by_topic,
        "opportunities": opportunities,
        "gap_analysis":  gap_analysis,
        "guidance":      guidance,
    }

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n✅  benchmarks.json written → {OUTPUT_PATH}")
    print(f"    Topics : {', '.join(by_topic.keys())}")
    print(f"    Undervalued posts : {len(opportunities['undervalued'])}")
    print(f"    Overexposed posts : {len(opportunities['overexposed'])}")
    print(f"    Seasonal gaps     : {', '.join(gap_analysis['seasonal_gaps'].keys()) or 'none'}")


if __name__ == "__main__":
    build()
