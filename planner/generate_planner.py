"""
generate_planner.py
===================
Reads the scored posts dataset and writes planner_data.json.

For each month, computes:
  - Which topics scored highest historically
  - Which topics are missing or underrepresented
  - 2-3 specific post ideas based on that month's winners

Run once after build_benchmarks.py, or whenever the CSV is refreshed.

Usage:
    python3 generate_planner.py

Output:
    planner_data.json  (project root)
"""

import json
import re
import pandas as pd
from pathlib import Path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "scoring"))
from post_value_score import compute_value_scores

DATA_PATH   = Path(__file__).parent.parent / "data" / "facility_news_posts_export.csv"
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "planner_data.json"

ALL_TOPICS = [
    "Aquatics & Swim School",
    "Equipment Upgrades",
    "Facility Operations",
    "Group Fitness",
    "Health & Wellness",
    "Programs & Enrolments",
    "Trainer Spotlight",
]

# Winning title format per topic (used to generate post ideas)
TITLE_TEMPLATES = {
    "Aquatics & Swim School": [
        "Swim School Enrolments Now Open for Term [N]",
        "The Surprising Health Benefits of Aqua Aerobics",
        "Upcoming Temporary Closure: [Pool Name] Maintenance",
    ],
    "Equipment Upgrades": [
        "New Upgrade: Brand New [Equipment] Arriving Soon!",
        "Exciting New Addition: [Equipment] Now at Our Facility",
    ],
    "Facility Operations": [
        "[Season] Facility Opening Hours Schedule",
        "Public Holiday Opening Hours – [Holiday Name]",
        "Upcoming Temporary Closure: [Area] Maintenance",
    ],
    "Group Fitness": [
        "Why You Should Add [Class] to Your Weekly Routine",
        "Group Fitness Timetable Update – Effective [Month]",
        "The Surprising Health Benefits of [Class]",
    ],
    "Health & Wellness": [
        "The Surprising Health Benefits of [X]",
        "Community Wellness [Event Name] & Seminar",
    ],
    "Programs & Enrolments": [
        "School Holiday Activity Program – Bookings Open!",
        "Swim School Enrolments Now Open for Term [N]",
    ],
    "Trainer Spotlight": [
        "Trainer Spotlight: Meet [Name]",
    ],
}

# Ideal reading time per topic (minutes)
IDEAL_READ = {
    "Aquatics & Swim School": "2–3 min",
    "Equipment Upgrades":     "1–2 min",
    "Facility Operations":    "1–2 min",
    "Group Fitness":          "2–4 min",
    "Health & Wellness":      "2–4 min",
    "Programs & Enrolments":  "1–3 min",
    "Trainer Spotlight":      "2–3 min",
}

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March",    4: "April",
    5: "May",     6: "June",     7: "July",      8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def strip_update(title: str) -> str:
    return re.sub(r"\s*-\s*Update\s*\d+$", "", title, flags=re.IGNORECASE).strip()


def r(val, dp=1):
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return round(float(val), dp)


def build_post_ideas(top_topics: list, month_name: str) -> list:
    """Generate 2-3 post ideas from the top performing topics for a month."""
    ideas = []
    for topic in top_topics[:3]:
        templates = TITLE_TEMPLATES.get(topic, [])
        if not templates:
            continue
        ideas.append({
            "topic":        topic,
            "title_idea":   templates[0],
            "reading_time": IDEAL_READ.get(topic, "2–3 min"),
            "why":          f"Historically strong performer in {month_name}.",
        })
    return ideas


def build():
    print(f"Loading {DATA_PATH} ...")
    raw = pd.read_csv(DATA_PATH)
    df  = compute_value_scores(raw)

    df["month_num"]  = pd.to_datetime(df["post_date"]).dt.month
    df["month_name"] = pd.to_datetime(df["post_date"]).dt.strftime("%B")

    # Per-month, per-topic aggregation
    grouped = df.groupby(["month_num", "month_name", "topic_category"]).agg(
        post_count=("value_score", "count"),
        avg_score=("value_score", "mean"),
    ).reset_index()

    # Overall avg posts per topic per month (to detect underrepresentation)
    overall_avg_per_topic = (
        grouped.groupby("topic_category")["post_count"].mean().to_dict()
    )

    planner = {}

    for month_num in range(1, 13):
        month_name = MONTH_NAMES[month_num]
        month_data = grouped[grouped["month_num"] == month_num].copy()

        if month_data.empty:
            # No historical data for this month
            planner[month_name] = {
                "month_num":        month_num,
                "top_topics":       [],
                "missing_topics":   ALL_TOPICS,
                "post_ideas":       build_post_ideas(ALL_TOPICS[:3], month_name),
                "note":             "No historical data for this month — all topics are opportunities.",
            }
            continue

        # Sort topics by avg score descending
        month_data = month_data.sort_values("avg_score", ascending=False)
        topics_present = month_data["topic_category"].tolist()

        # Top topics (score above overall avg)
        overall_avg = df["value_score"].mean()
        top_topics = month_data[
            month_data["avg_score"] >= overall_avg
        ]["topic_category"].tolist()

        # Missing topics (not posted at all this month historically)
        missing_topics = [t for t in ALL_TOPICS if t not in topics_present]

        # Underrepresented (posted but below half their usual volume)
        underrep = []
        for _, row in month_data.iterrows():
            topic = row["topic_category"]
            avg   = overall_avg_per_topic.get(topic, 1)
            if row["post_count"] < avg * 0.5:
                underrep.append(topic)

        # Top 3 posts this month (deduplicated by base title)
        month_posts = df[df["month_num"] == month_num].copy()
        month_posts["base_title"] = month_posts["title"].apply(strip_update)
        top_posts = (
            month_posts.sort_values("value_score", ascending=False)
            .drop_duplicates("base_title")
            .head(3)[["base_title", "topic_category", "value_score",
                       "estimated_reading_time_minutes"]]
        )

        planner[month_name] = {
            "month_num": month_num,
            "top_topics": [
                {
                    "topic":     row["topic_category"],
                    "avg_score": r(row["avg_score"]),
                    "posts":     int(row["post_count"]),
                }
                for _, row in month_data.head(3).iterrows()
            ],
            "missing_topics":        missing_topics,
            "underrepresented_topics": underrep,
            "post_ideas":            build_post_ideas(
                top_topics if top_topics else topics_present, month_name
            ),
            "top_historical_posts": [
                {
                    "title":      row["base_title"],
                    "topic":      row["topic_category"],
                    "score":      r(row["value_score"]),
                    "read_mins":  int(row["estimated_reading_time_minutes"]),
                }
                for _, row in top_posts.iterrows()
            ],
        }

    out = {
        "_meta": {
            "generated":   pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "source":      "facility_news_posts_export.csv",
            "description": "Monthly content planning data for the marketing team.",
        },
        "months": planner,
    }

    OUTPUT_PATH.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n✅  planner_data.json written → {OUTPUT_PATH}")
    print(f"    Months covered: {', '.join(planner.keys())}")


if __name__ == "__main__":
    build()
