/**
 * app.js
 * ======
 * Client-side logic for the Marketing Content Optimization System.
 * Handles scoring, AI suggestions, planner tab, and dark mode.
 */

// ── State ──────────────────────────────────────────────────────────────────
let BENCH   = null;
let PLANNER = null;

// ── Load benchmarks.json ───────────────────────────────────────────────────
async function loadBenchmarks() {
  try {
    const res = await fetch("/data/benchmarks.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    BENCH = await res.json();
    renderLegend();
  } catch (e) {
    // Fallback for static server (python3 -m http.server)
    try {
      const res2 = await fetch("../data/benchmarks.json");
      if (!res2.ok) throw new Error(`HTTP ${res2.status}`);
      BENCH = await res2.json();
      renderLegend();
    } catch {
      showError("Could not load benchmarks.json — make sure you've run build_benchmarks.py first.");
    }
  }
}

// ── Load planner_data.json ─────────────────────────────────────────────────
async function loadPlanner() {
  try {
    const res = await fetch("/data/planner_data.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    PLANNER = await res.json();
  } catch {
    try {
      const res2 = await fetch("../data/planner_data.json");
      if (!res2.ok) throw new Error();
      PLANNER = await res2.json();
    } catch {
      console.warn("planner_data.json not loaded — run generate_planner.py first.");
    }
  }
}

// ── Tab switching ──────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.querySelectorAll(".tab-btn").forEach(b => {
    if (b.textContent.toLowerCase().includes(name === "checker" ? "post" : "write")) {
      b.classList.add("active");
    }
  });
}

// ── Render planner tab ─────────────────────────────────────────────────────
function renderPlanner() {
  const month = document.getElementById("planner-month").value;
  if (!month || !PLANNER) return;

  const data = PLANNER.months[month];
  document.getElementById("planner-month-label").textContent = month;
  document.getElementById("planner-results").style.display = "block";
  document.getElementById("planner-empty").style.display   = "none";

  // Post ideas
  const ideas = data.post_ideas.map(idea => `
    <div class="idea-card">
      <div class="idea-topic">${idea.topic}</div>
      <div class="idea-title">${idea.title_idea}</div>
      <div class="idea-meta">⏱ ${idea.reading_time} &nbsp;·&nbsp; ${idea.why}</div>
    </div>`).join("");
  document.getElementById("idea-list").innerHTML = ideas || "<p style='color:var(--muted);font-size:.85rem;'>No ideas available for this month.</p>";

  // Topic coverage tags
  const allTopics = [
    "Aquatics & Swim School", "Equipment Upgrades", "Facility Operations",
    "Group Fitness", "Health & Wellness", "Programs & Enrolments", "Trainer Spotlight",
  ];
  const missing = data.missing_topics || [];
  const underrep = data.underrepresented_topics || [];
  const topTopics = (data.top_topics || []).map(t => t.topic);

  const tags = allTopics.map(t => {
    if (missing.includes(t))   return `<span class="tag tag-miss">✕ ${t}</span>`;
    if (underrep.includes(t))  return `<span class="tag tag-low">↓ ${t}</span>`;
    if (topTopics.includes(t)) return `<span class="tag tag-good">✓ ${t}</span>`;
    return `<span class="tag" style="background:var(--bg);border:1px solid var(--border);color:var(--muted);">${t}</span>`;
  }).join("");
  document.getElementById("topic-tags").innerHTML = tags;

  // Top historical posts
  const posts = data.top_historical_posts || [];
  if (posts.length) {
    document.getElementById("planner-history-card").style.display = "block";
    const rows = posts.map(p => `
      <tr>
        <td>${p.title}</td>
        <td style="text-align:center;">
          <span class="score-badge" style="background:${barColor(p.score)}22;color:${barColor(p.score)};border:1px solid ${barColor(p.score)}44;">
            ${p.score}
          </span>
        </td>
        <td style="text-align:center;">${p.read_mins} min</td>
      </tr>`).join("");
    document.getElementById("planner-top-posts").innerHTML = `
      <table>
        <thead><tr><th>Title</th><th>Score</th><th>Read</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }
}

// ── Word count & reading time ──────────────────────────────────────────────
function updateWordCount() {
  const text  = document.getElementById("inp-content").value.trim();
  const words = text ? text.split(/\s+/).length : 0;
  const mins  = Math.max(1, Math.round(words / 200));
  document.getElementById("word-count").textContent = words.toLocaleString();
  document.getElementById("read-time").textContent  = mins;
}

function getTitleLen() {
  const v = document.getElementById("inp-title").value.length;
  document.getElementById("title-len").textContent = v;
}

// ── Scoring helpers ────────────────────────────────────────────────────────
function readingTimeScore(mins) {
  if (mins >= 2 && mins <= 4) return 100;
  if (mins < 2)  return Math.max(0, 100 - (2 - mins) * 35);
  return Math.max(0, 100 - (mins - 4) * 20);
}

// Estimate a pseudo-score without the real view_count & SEO matrix
// We use benchmark medians for the metric distributions as stand-ins,
// then allow the reading-time dimension to show real signal.
// The "projected" score uses category benchmarks to show what this post
// SHOULD achieve if written to the winning formula.
function projectScore(category, readMins) {
  const b  = BENCH.by_topic[category];
  const ov = BENCH.overall;

  // Use category avg percentile position as proxy for metric scores
  const avgViewPct   = (b.avg_views   / ov.view_count.p90)   * 100;
  const avgLinkPct   = (b.avg_seo_linkdex  / 90)  * 100;
  const avgContentPct= (b.avg_seo_content  / 90)  * 100;
  const rtScore      = readingTimeScore(readMins);

  const score =
    Math.min(100, avgViewPct)  * 0.30 +
    Math.min(100, avgLinkPct)  * 0.25 +
    Math.min(100, avgContentPct) * 0.25 +
    rtScore * 0.20;

  return Math.round(score * 10) / 10;
}

function getTier(score) {
  if (score >= 80) return { label: "Gold",       cls: "tier-gold"   };
  if (score >= 60) return { label: "Silver",     cls: "tier-silver" };
  if (score >= 40) return { label: "Bronze",     cls: "tier-bronze" };
  return                 { label: "Needs Work",  cls: "tier-poor"   };
}

function tierTagline(tier) {
  const map = {
    "Gold":       "Top-tier projection — write to the winning formula below.",
    "Silver":     "Solid projection — small SEO or depth improvements push to Gold.",
    "Bronze":     "Needs improvement — focus on SEO scores and content depth.",
    "Needs Work": "Below benchmark — review category guidance and title format.",
  };
  return map[tier] || "";
}

function barColor(score) {
  if (score >= 80) return "#b45309";
  if (score >= 60) return "#2563eb";
  if (score >= 40) return "#92400e";
  return "#991b1b";
}

// ── Reading-time dimension ─────────────────────────────────────────────────
function readTimeDim(mins, bench) {
  const score  = readingTimeScore(mins);
  const ideal  = bench.brief_template.ideal_reading_time;
  let badge, badgeCls, tip;

  if (mins >= 2 && mins <= 4) {
    badge = "Ideal"; badgeCls = "badge-green";
    tip = `${mins} min is in the sweet spot (${ideal.min}–${ideal.max} min for this category).`;
  } else if (mins < 2) {
    badge = "Too Short"; badgeCls = "badge-red";
    tip = BENCH.guidance.reading_time.too_short;
  } else {
    badge = "Long"; badgeCls = "badge-yellow";
    tip = BENCH.guidance.reading_time.too_long;
  }

  return { icon: "⏱", label: `Reading Time · ${mins} min`, badge, badgeCls, tip };
}

// ── Category keywords for content check ───────────────────────────────────
const CATEGORY_KEYWORDS = {
  "Aquatics & Swim School":  ["swim", "aqua", "pool"],
  "Equipment Upgrades":      ["upgrade", "equipment"],
  "Facility Operations":     ["hours", "schedule", "closure"],
  "Group Fitness":           ["fitness", "class", "routine"],
  "Health & Wellness":       ["health", "wellness", "benefit"],
  "Programs & Enrolments":   ["program", "enrolment", "booking"],
  "Trainer Spotlight":       ["trainer", "coach"],
};

// ── Title format patterns per category (top 2) ────────────────────────────
const TITLE_FORMATS = {
  "Aquatics & Swim School": [
    { test: t => /swim school|enrolment/.test(t), label: "Swim School Enrolments Now Open for Term [N]" },
    { test: t => /surprising|benefit/.test(t),    label: "The Surprising Health Benefits of [X]" },
  ],
  "Equipment Upgrades": [
    { test: t => /new upgrade|arriving/.test(t),  label: "New Upgrade: Brand New [Equipment] Arriving Soon!" },
    { test: t => /brand new/.test(t),             label: "New Upgrade: Brand New [Equipment] Arriving Soon!" },
  ],
  "Facility Operations": [
    { test: t => /opening hours|schedule/.test(t),label: "[Season] Facility Opening Hours Schedule" },
    { test: t => /closure|maintenance/.test(t),   label: "Upcoming Temporary Closure: [Area] Maintenance" },
  ],
  "Group Fitness": [
    { test: t => /why you should/.test(t),        label: "Why You Should Add [X] to Your Weekly Routine" },
    { test: t => /timetable|group fitness/.test(t),label: "Group Fitness Timetable Update – Effective [Month]" },
  ],
  "Health & Wellness": [
    { test: t => /surprising|benefit/.test(t),    label: "The Surprising Health Benefits of [X]" },
    { test: t => /community|wellness/.test(t),    label: "Community Wellness [Event Name]" },
  ],
  "Programs & Enrolments": [
    { test: t => /school holiday|bookings/.test(t),label: "School Holiday Activity Program – Bookings Open!" },
    { test: t => /enrolment|term/.test(t),        label: "Swim School Enrolments Now Open for Term [N]" },
  ],
  "Trainer Spotlight": [
    { test: t => /trainer spotlight|meet/.test(t),label: "Trainer Spotlight: Meet [Name]" },
    { test: t => true,                            label: "Trainer Spotlight: Meet [Name]" },
  ],
};

// ── Extract topic noun from title ──────────────────────────────────────────
function extractTopic(title) {
  // Strip common wrapper phrases to isolate the subject
  let topic = title
    .replace(/why you should add|to your weekly routine/gi, "")
    .replace(/the surprising health benefits of/gi, "")
    .replace(/new upgrade: brand new|arriving soon!?/gi, "")
    .replace(/upcoming temporary closure:|maintenance/gi, "")
    .replace(/trainer spotlight: meet/gi, "")
    .replace(/community wellness/gi, "")
    .replace(/swim school enrolments now open for/gi, "")
    .replace(/school holiday activity program|bookings open!?/gi, "")
    .replace(/- update \d+/gi, "")
    .replace(/[–—:!?]/g, "")
    .trim()
    .replace(/\s+/g, " ");

  // If nothing was stripped (title didn't match any pattern),
  // take first 3 meaningful words as the topic
  if (topic.length > 40 || topic === title.trim()) {
    const words = topic.split(" ").filter(w => w.length > 2);
    topic = words.slice(0, 3).join(" ");
  }

  return topic || "this topic";
}

// ── Build two specific title suggestions ──────────────────────────────────
function buildTitleSuggestions(title, category) {
  const topic = extractTopic(title);
  const Topic = topic.charAt(0).toUpperCase() + topic.slice(1);
  const formats = TITLE_FORMATS[category] || [];
  const low = title.toLowerCase();

  // Check if title already matches a winning format
  const matched = formats.some(f => f.test(low));

  // Generate two concrete suggestions from top 2 formats
  const suggestions = {
    "Aquatics & Swim School":  [`The Surprising Health Benefits of ${Topic}`, `Swim School Enrolments Now Open – ${Topic}`],
    "Equipment Upgrades":      [`New Upgrade: Brand New ${Topic} Arriving Soon!`, `Exciting New Addition: ${Topic} Now at Our Facility`],
    "Facility Operations":     [`Spring Facility Opening Hours – ${Topic}`, `Important Update: ${Topic} Schedule Changes`],
    "Group Fitness":           [`Why You Should Add ${Topic} to Your Weekly Routine`, `The Surprising Health Benefits of ${Topic}`],
    "Health & Wellness":       [`The Surprising Health Benefits of ${Topic}`, `Community Wellness: ${Topic} Seminar`],
    "Programs & Enrolments":   [`School Holiday Activity Program – ${Topic} Bookings Open!`, `${Topic} Enrolments Now Open`],
    "Trainer Spotlight":       [`Trainer Spotlight: Meet ${Topic}`, `Meet Our Expert: ${Topic}`],
  };

  return { matched, alts: suggestions[category] || [`The ${Topic} Guide`, `Everything You Need to Know About ${Topic}`] };
}

// ── Build suggestions section ──────────────────────────────────────────────
function buildSuggestions(title, content, category) {
  const cards = [];
  const titleLow   = title.toLowerCase();
  const contentLow = content.toLowerCase();
  const combined   = titleLow + " " + contentLow;

  // 1. Title format
  const { matched, alts } = buildTitleSuggestions(title, category);
  if (matched) {
    cards.push(`<div class="suggestion pass">
      <div class="s-label">✅ Title Format</div>
      Your title matches a winning format for this category. Good start.
    </div>`);
  } else {
    cards.push(`<div class="suggestion warn">
      <div class="s-label">✏️ Title Format — try a proven format</div>
      Top posts in this category use these formats:
      <div class="s-try">→ ${alts[0]}</div>
      <div class="s-try">→ ${alts[1]}</div>
    </div>`);
  }

  // 2. Keyword presence
  const keywords = CATEGORY_KEYWORDS[category] || [];
  const hasKeyword = keywords.some(k => combined.includes(k));
  if (hasKeyword) {
    cards.push(`<div class="suggestion pass">
      <div class="s-label">✅ Category Keyword</div>
      Your content includes a relevant keyword for this category (${keywords.join(", ")}).
    </div>`);
  } else {
    cards.push(`<div class="suggestion warn">
      <div class="s-label">🔍 Category Keyword Missing</div>
      Your title and content don't mention a core keyword for this category.
      Try including one of: <strong>${keywords.join(", ")}</strong>.
    </div>`);
  }

  // 3. Subheadings
  const lines = content.split("\n").map(l => l.trim()).filter(Boolean);
  const hasSubheadings = lines.some(l =>
    l.startsWith("#") ||
    (l.length < 60 && l === l.toUpperCase() && l.length > 4) ||
    /^[A-Z][^.!?]{5,50}$/.test(l) && lines.indexOf(l) > 0
  );
  if (hasSubheadings) {
    cards.push(`<div class="suggestion pass">
      <div class="s-label">✅ Content Structure</div>
      Subheadings detected — good for readability and SEO.
    </div>`);
  } else {
    cards.push(`<div class="suggestion warn">
      <div class="s-label">📋 Add Subheadings</div>
      No subheadings found. Breaking your content into 2–3 sections
      improves readability and helps readers scan quickly.
    </div>`);
  }

  return cards.join("");
}

// ── Render dimension row ───────────────────────────────────────────────────
function renderDim({ icon, label, badge, badgeCls, tip }) {
  return `
    <div class="dim">
      <div class="dim-icon">${icon}</div>
      <div class="dim-body">
        <div class="dim-label">${label}</div>
        <div class="dim-tip">${tip}</div>
      </div>
      <div class="dim-badge ${badgeCls}">${badge}</div>
    </div>`;
}

// ── Guidance boxes ─────────────────────────────────────────────────────────
function buildGuidance(tier, readMins, category, score, bench) {
  const boxes = [];
  const g = BENCH.guidance;

  // Tier guidance
  const tierCls = { "Gold": "ok", "Silver": "info", "Bronze": "warn", "Needs Work": "bad" };
  boxes.push(`<div class="guidance-box ${tierCls[tier]}">
    <strong>🏆 Value Score · ${score} / 100</strong>
    ${g.tiers[tier]}
  </div>`);

  // Reading time guidance (only show if outside ideal band)
  if (readMins < 2) {
    boxes.push(`<div class="guidance-box warn">
      <strong>⏱ Content Too Short</strong>
      ${g.reading_time.too_short}
    </div>`);
  } else if (readMins > 4) {
    boxes.push(`<div class="guidance-box warn">
      <strong>⏱ Content Length</strong>
      ${g.reading_time.too_long}
    </div>`);
  }

  return boxes.join("");
}

// ── Brief template section ─────────────────────────────────────────────────
function renderBrief(bench) {
  const t = bench.brief_template;
  const fmts = t.winning_title_formats.map(f => `<li>${f}</li>`).join("");

  return `
    <div class="brief-grid" style="grid-template-columns:1fr;">
      <div class="brief-item">
        <div class="bi-label">Ideal Reading Time</div>
        <div class="bi-val">${t.ideal_reading_time.min}–${t.ideal_reading_time.max} min</div>
      </div>
    </div>
    <div class="card-title" style="margin-bottom:8px;">Winning Title Formats</div>
    <ul class="formats-list">${fmts}</ul>`;
}

// ── Top posts table ────────────────────────────────────────────────────────
function renderTopPosts(posts) {
  const rows = posts.map(p => {
    const tier = getTier(p.value_score);
    const color = barColor(p.value_score);
    return `<tr>
      <td>${p.title.replace(/\s*-\s*Update\s*\d+$/i, "")}</td>
      <td style="text-align:center;">
        <span class="score-badge" style="background:${color}22;color:${color};border:1px solid ${color}44;">
          ${p.value_score}
        </span>
      </td>
      <td style="text-align:center;">${p.read_mins} min</td>
    </tr>`;
  }).join("");

  return `<table>
    <thead><tr><th>Title</th><th>Score</th><th>Read</th></tr></thead>
    <tbody>${rows}</tbody>
  </table>`;
}

// ── Toggle benchmarks ──────────────────────────────────────────────────────
function toggleBenchmarks() {
  const content = document.getElementById("legend-content");
  const toggle  = document.getElementById("bench-toggle");
  const visible = content.style.display !== "none";
  content.style.display = visible ? "none" : "block";
  toggle.textContent    = visible ? "▼ Show" : "▲ Hide";
}

// ── Legend sidebar ─────────────────────────────────────────────────────────
function renderLegend() {
  if (!BENCH) return;
  const ov = BENCH.overall;
  const rows = [
    ["Total posts analysed",  ov.total_posts],
    ["Avg value score",       ov.value_score.mean],
    ["Median value score",    ov.value_score.median],
    ["Top 25% threshold",     ov.value_score.p75],
    ["Top 10% threshold",     ov.value_score.p90],
    ["Avg views per post",    ov.view_count.mean.toLocaleString()],
    ["Ideal reading time",    `${ov.reading_time_minutes.ideal_min}–${ov.reading_time_minutes.ideal_max} min`],
  ];
  document.getElementById("legend-content").innerHTML =
    rows.map(([l, v]) => `<div class="legend-row"><span class="legend-label">${l}</span><span class="legend-val">${v}</span></div>`).join("");
}

// ── Main check ────────────────────────────────────────────────────────────
function runCheck() {
  clearError();
  const title    = document.getElementById("inp-title").value.trim();
  const category = document.getElementById("inp-category").value;
  const content  = document.getElementById("inp-content").value.trim();

  if (!title)    { showError("Please enter a post title."); return; }
  if (!category) { showError("Please select a topic category."); return; }
  if (!content)  { showError("Please paste your content body."); return; }
  if (!BENCH)    { showError("Benchmarks not loaded. Check that benchmarks.json exists."); return; }

  // Show loader
  document.getElementById("loader").style.display       = "block";
  document.getElementById("score-card").style.display    = "none";
  document.getElementById("guidance-card").style.display = "none";
  document.getElementById("btn-check").disabled     = true;

  setTimeout(() => {
    try {
      const words   = content.split(/\s+/).length;
      const readMins = Math.max(1, Math.min(4, Math.round(words / 200)));
      const bench   = BENCH.by_topic[category];
      const score   = projectScore(category, readMins);
      const { label: tier, cls: tierCls } = getTier(score);

      // ── Hero
      document.getElementById("hero").innerHTML = `
        <div class="label">Projected Value Score</div>
        <div class="number" style="color:${barColor(score)}">${score}</div>
        <div class="tier ${tierCls}">${tier}</div>
        <div class="tagline">${tierTagline(tier)}</div>`;

      // ── Score bar
      const bar = document.getElementById("score-bar");
      bar.style.width = score + "%";
      bar.style.background = barColor(score);
      document.getElementById("bar-publish-line").textContent =
        "Publish min " + bench.brief_template.min_value_score_before_publish;

      // ── Dimensions (reading time only now)
      const dims = [
        readTimeDim(readMins, bench),
      ];
      document.getElementById("dimensions").innerHTML = dims.map(renderDim).join("");

      // ── Guidance
      document.getElementById("guidance-boxes").innerHTML =
        buildGuidance(tier, readMins, category, score, bench);

      // ── Reset AI section
      document.getElementById("ai-title-suggestions").style.display = "none";
      document.getElementById("ai-title-suggestions").innerHTML = "";
      document.getElementById("ai-content-suggestions").style.display = "none";
      document.getElementById("ai-content-suggestions").innerHTML = "";
      document.getElementById("btn-ai").disabled = false;

      // ── Show bottom sections
      document.getElementById("bottom-sections").style.display = "block";

      // ── Brief template
      document.getElementById("brief-section").innerHTML = renderBrief(bench);

      // ── Top posts
      document.getElementById("top-posts-table").innerHTML =
        renderTopPosts(bench.top_posts);

      // Show results
      document.getElementById("loader").style.display       = "none";
      document.getElementById("score-card").style.display    = "block";
      document.getElementById("guidance-card").style.display = "block";
    } catch (err) {
      showError("Scoring error: " + err.message);
      document.getElementById("loader").style.display = "none";
    }
    document.getElementById("btn-check").disabled = false;
  }, 400);
}

function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.style.display = "block";
}
function clearError() {
  document.getElementById("error-msg").style.display = "none";
}

// ── AI Suggestions ─────────────────────────────────────────────────────────
async function getAISuggestions() {
  const title    = document.getElementById("inp-title").value.trim();
  const category = document.getElementById("inp-category").value;
  const content  = document.getElementById("inp-content").value.trim();

  if (!title || !category || !content) {
    showError("Please fill in all fields before getting AI suggestions.");
    return;
  }

  const btn = document.getElementById("btn-ai");
  btn.disabled = true;

  // Show spinners inline
  const spinner = `<div class="ai-spinner"><div class="spin"></div>Generating…</div>`;
  const titleEl   = document.getElementById("ai-title-suggestions");
  const contentEl = document.getElementById("ai-content-suggestions");
  titleEl.innerHTML   = spinner;
  titleEl.style.display = "block";
  contentEl.innerHTML   = spinner;
  contentEl.style.display = "block";

  try {
    const res = await fetch("/api/suggest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, category, content }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();

    // Title suggestions inline under title field
    const titleItems = (data.title_suggestions || [])
      .map(t => `<div class="ai-tip">${t}</div>`).join("");
    titleEl.innerHTML = `
      <div class="ai-result">
        <div class="ai-section-title">✨ AI Title Ideas</div>
        ${titleItems || "<div class='ai-tip'>No suggestions returned.</div>"}
      </div>`;

    // Content suggestions inline under content field
    const contentItems = (data.content_suggestions || [])
      .map(c => `<div class="ai-tip">${c}</div>`).join("");
    const overall = data.overall_tip
      ? `<div class="ai-overall">💡 ${data.overall_tip}</div>` : "";
    contentEl.innerHTML = `
      <div class="ai-result">
        <div class="ai-section-title">✨ AI Content Improvements</div>
        ${contentItems || "<div class='ai-tip'>No suggestions returned.</div>"}
        ${overall}
      </div>`;

  } catch (err) {
    const errMsg = `<div style="color:var(--red);font-size:.83rem;">
      Could not reach AI service — make sure app.py is running and your GEMINI_API_KEY is set in .env
    </div>`;
    titleEl.innerHTML   = errMsg;
    contentEl.innerHTML = errMsg;
  }
  btn.disabled = false;
}

// ── Dark mode ──────────────────────────────────────────────────────────────
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.textContent = theme === "dark" ? "☀️" : "🌙";
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  const next    = current === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem("theme", next);
}

function initTheme() {
  const saved = localStorage.getItem("theme") || "light";
  applyTheme(saved);
}

// ── Events ─────────────────────────────────────────────────────────────────
document.getElementById("inp-content").addEventListener("input", updateWordCount);
document.getElementById("inp-title").addEventListener("input", getTitleLen);

// ── Init ───────────────────────────────────────────────────────────────────
initTheme();
loadBenchmarks();
loadPlanner();
