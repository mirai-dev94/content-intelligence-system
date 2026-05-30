
# Content Intelligence System· v1

A Python-based content intelligence system that analyzes historical content performance data, generates benchmark models, and provides data-driven recommendations to support content optimization decisions.

## Background

This project was inspired by a real-world content management and digital marketing workflow.

The original business challenge involved evaluating large volumes of published content and identifying patterns associated with higher engagement and stronger SEO performance.

To demonstrate the underlying technical approach without exposing proprietary information, this repository uses a synthetic dataset that replicates the structure and characteristics of real-world content analytics data.

---
## Data & Privacy Notice

This repository does not contain any proprietary, confidential, or personally identifiable information.

The dataset included in this project is a synthetic dataset created solely for demonstration and educational purposes. The structure of the data is inspired by real-world content analytics workflows, but all records, metrics, and article information have been anonymized or generated independently.

This project demonstrates the technical approach, system design, and analytical methodology rather than any specific organization's data.

## Technical Highlights

- Python-based analytics pipeline
- Benchmark generation from historical datasets
- Weighted scoring model for content evaluation
- Rule-based recommendation engine
- Opportunity detection (high SEO / low visibility content)
- Gap analysis for content planning
- HTML-based evaluation interface
- JSON benchmark generation and consumption

## What's inside

```
marketing_optimizer/
├── data/
│   └── facility_news_posts_export.csv   ← your source data
├── post_value_score.py                  ← scoring engine (library)
├── build_benchmarks.py                  ← benchmark generator (run once)
├── benchmarks.json                      ← generated benchmarks (auto-created)
├── post_score_checker.html              ← marketing team's browser tool
├── requirements.txt
└── README.md
```

---

## How it works

### Value Score (0–100)

Each post is scored on four marketing metrics, each percentile-ranked
against the full dataset so the score reflects *relative* performance:

| Metric                        | Weight |
|-------------------------------|--------|
| View Count                    | 30 %   |
| SEO Linkdex (focus keyword)   | 25 %   |
| SEO Content Score             | 25 %   |
| Estimated Reading Time        | 20 %   |

Reading time is scored against an ideal engagement band (2–4 min)
rather than raw percentile — more is not always better.

### Value Tiers

| Tier        | Score  | Meaning                                       |
|-------------|--------|-----------------------------------------------|
| Gold        | 80–100 | Top performer — study and replicate           |
| Silver      | 60–79  | Solid — small improvements push to Gold       |
| Bronze      | 40–59  | Needs work — review SEO and content depth     |
| Needs Work  | 0–39   | Underperformer — prioritise SEO or topic rethink |

### Topic Categories (inferred from titles)

- Aquatics & Swim School
- Equipment Upgrades
- Facility Operations
- Group Fitness
- Health & Wellness
- Programs & Enrolments
- Trainer Spotlight

---

## Quick-start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate benchmarks

Run this once — or whenever you add new posts to the CSV:

```bash
python build_benchmarks.py
```

This reads `data/facility_news_posts_export.csv`, scores all 300 posts,
and writes `benchmarks.json`.

### 3. Open the checker tool

Open `post_score_checker.html` in any modern browser (Chrome, Edge, Firefox).

> **Important:** Open from the same folder as `benchmarks.json`.
> If you double-click the file it may fail to load `benchmarks.json`
> due to browser CORS restrictions. Use a simple local server instead:
>
> ```bash
> # Python (recommended)
> python -m http.server 8080
> # then open http://localhost:8080/post_score_checker.html
>
> # Or use the VS Code Live Server extension
> ```

### 4. Check a post

Fill in:
- **Post Title** — the full title you plan to publish
- **Topic Category** — pick from the dropdown
- **Content Body** — paste your draft text

Click **Analyse Post** and the tool will:
1. Estimate reading time from word count
2. Project a Value Score against category benchmarks
3. Show a Tier rating (Gold / Silver / Bronze / Needs Work)
4. Give actionable SEO targets and title-format guidance
5. Compare against the top 5 posts in that category

The marketing matrix numbers (view counts, SEO scores) are not shown
in the input form — they come from the benchmark averages automatically.

---

## What the benchmark tool produces

`benchmarks.json` contains:

| Section            | Contents                                                       |
|--------------------|----------------------------------------------------------------|
| `overall`          | Site-wide stats: avg/median score, view counts, SEO targets    |
| `by_topic`         | Per-category benchmarks + post brief template                  |
| `opportunities`    | Undervalued posts (high SEO, low views) & overexposed posts   |
| `gap_analysis`     | Underperforming topic categories + seasonal content gaps       |
| `guidance`         | Tier descriptions and SEO coaching tips                        |

### Post Brief Template (per category)

Each category section includes a ready-to-use brief:

```json
"brief_template": {
  "ideal_reading_time": { "min": 2, "max": 4 },
  "target_seo_linkdex": 70.0,
  "target_seo_content": 75.0,
  "min_value_score_before_publish": 52.3,
  "winning_title_formats": [
    "Why You Should Add [X] to Your Weekly Routine",
    "The [Adjective] Health Benefits of [X]"
  ]
}
```

---

## Opportunities identified in current dataset

Run `build_benchmarks.py` and open `benchmarks.json` to see the full lists.
High-level findings from 300 posts (2023–2026):

- **Undervalued posts (10):** High SEO scores but low view counts.
  Action: promote via social media and internal linking.
- **Overexposed posts (10):** High views but weak SEO foundations.
  Action: refresh meta descriptions, headings, and keyword use.
- **Seasonal gap:** September has below-average post volume.
  Plan 1–2 extra posts in that month.

---

## Refreshing the data

1. Export a new CSV from your CMS in the same column format.
2. Place it in the `data/` folder (same filename, or update the path in `build_benchmarks.py`).
3. Re-run `python build_benchmarks.py`.
4. Refresh the browser — the HTML tool picks up the new `benchmarks.json` automatically.

---

## Roadmap (v2 ideas)

- [ ] Real-time SEO score input fields in the HTML checker
- [ ] CSV batch-check: score a list of drafted posts at once
- [ ] Chart view: scatter plot of views vs SEO score
- [ ] Export scored dataset to Excel for leadership reporting
- [ ] Seasonal content calendar generator
