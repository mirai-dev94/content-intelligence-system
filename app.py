"""
app.py
======
Flask server for the Marketing Content Optimization System v5.

Serves the HTML tool and provides the /api/suggest endpoint
for AI-powered title and content suggestions via Gemini.

Usage:
    python3 app.py

Then open: http://localhost:5000
"""

import json
import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

# Add scoring to path so Flask can import it
sys.path.insert(0, str(Path(__file__).parent / "scoring"))

app = Flask(__name__, static_folder=".", static_url_path="")

BASE_DIR      = Path(__file__).parent
BENCHMARKS    = BASE_DIR / "data" / "benchmarks.json"
PLANNER_DATA  = BASE_DIR / "data" / "planner_data.json"
OPPORTUNITIES = BASE_DIR / "data" / "opportunities.json"


# ── Static file routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("templates", "post_score_checker.html")

@app.route("/data/<path:filename>")
def serve_data(filename):
    return send_from_directory("data", filename)

@app.route("/templates/<path:filename>")
def serve_templates(filename):
    return send_from_directory("templates", filename)


# ── AI suggestions endpoint ────────────────────────────────────────────────

@app.route("/api/suggest", methods=["POST"])
def suggest():
    body     = request.get_json()
    title    = body.get("title", "").strip()
    category = body.get("category", "").strip()
    content  = body.get("content", "").strip()

    if not title or not category or not content:
        return jsonify({"error": "title, category and content are required"}), 400

    # Load top posts for this category from benchmarks
    top_posts = []
    try:
        bench = json.loads(BENCHMARKS.read_text())
        top_posts = bench.get("by_topic", {}).get(category, {}).get("top_posts", [])
        # Normalise key name for suggest.py
        top_posts = [{"title": p["title"], "score": p["value_score"]} for p in top_posts]
    except Exception:
        pass

    from ai.suggest import get_suggestions
    result = get_suggestions(title, category, content, top_posts)
    return jsonify(result)


# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🚀  Marketing Content Optimizer v5")
    print("   Open: http://localhost:5000\n")
    app.run(debug=True, port=5000)
