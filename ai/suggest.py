"""
ai/suggest.py
=============
Generates AI-powered title and content suggestions for a marketing news post.

Default provider: Google Gemini (gemini-2.5-flash)
To swap providers, update the PROVIDER constant and the corresponding
API call in get_suggestions(). The prompt and response parsing are
provider-agnostic.

Supported providers (update PROVIDER and install the relevant package):
  - "gemini"   : google-generativeai  →  GEMINI_API_KEY in .env
  - "openai"   : openai               →  OPENAI_API_KEY in .env
  - "anthropic": anthropic            →  ANTHROPIC_API_KEY in .env

Called by app.py — not run directly.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

# ── Provider configuration ─────────────────────────────────────────────────
# Change PROVIDER to switch LLM backends. Update your .env with the
# corresponding API key.
PROVIDER = "gemini"
MODEL    = "gemini-2.5-flash"


def build_prompt(title: str, category: str, content: str, top_posts: list) -> str:
    top_examples = "\n".join(
        f"- {p['title']} (score: {p['score']})" for p in top_posts[:3]
    )
    return f"""You are a marketing content advisor for a fitness and aquatics facility.

A writer has drafted a news post. Analyse it and provide specific, actionable suggestions.

POST DETAILS:
Title: {title}
Category: {category}
Content:
{content[:1500]}

TOP PERFORMING POSTS IN THIS CATEGORY (for reference):
{top_examples}

Respond ONLY with a JSON object in this exact format, no markdown, no preamble:
{{
  "title_suggestions": [
    "First specific title rewrite here",
    "Second specific title rewrite here"
  ],
  "content_suggestions": [
    "First specific content improvement here",
    "Second specific content improvement here",
    "Third specific content improvement here"
  ],
  "overall_tip": "One sentence summary of the biggest improvement opportunity"
}}

Rules:
- Title suggestions must be specific rewrites, not templates with [X] placeholders
- Content suggestions must be concrete and actionable, not generic advice
- Keep each suggestion under 20 words
- Base suggestions on what works for this category and facility type"""


def _parse_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown fences."""
    text = text.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > start:
        text = text[start:end]
    return json.loads(text)


def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model  = genai.GenerativeModel(MODEL)
    result = model.generate_content(prompt)
    return result.text


def _call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    result = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return result.choices[0].message.content


def _call_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    result = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    return result.content[0].text


PROVIDERS = {
    "gemini":    _call_gemini,
    "openai":    _call_openai,
    "anthropic": _call_anthropic,
}


def get_suggestions(title: str, category: str, content: str, top_posts: list) -> dict:
    """
    Call the configured LLM provider and return structured suggestions.
    Returns a dict with title_suggestions, content_suggestions, overall_tip.
    """
    try:
        caller = PROVIDERS.get(PROVIDER)
        if not caller:
            raise ValueError(f"Unknown provider: {PROVIDER}. Choose from: {list(PROVIDERS.keys())}")

        prompt = build_prompt(title, category, content, top_posts)
        text   = caller(prompt)
        print(f"=== {PROVIDER} response ===\n{text[:400]}\n===")
        return _parse_response(text)

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        return {
            "title_suggestions":   ["Could not parse AI response — try again."],
            "content_suggestions": ["Could not parse AI response — try again."],
            "overall_tip":         "API returned an unexpected format.",
        }
    except Exception as e:
        print(f"API error: {e}")
        return {
            "title_suggestions":   [],
            "content_suggestions": [],
            "overall_tip":         f"Error: {str(e)}",
        }
