"""
generate_html.py
Takes the structured data dict from analyze.py and renders the full HTML dashboard.
"""

import json


# ── SLA RISK HELPERS ──────────────────────────────────────────────────────────

def _sla_risk(pct: float) -> tuple[str, str, str]:
    """Returns (css_class, badge_class, label)"""
    if pct >= 40:
        return "critical", "critical",  f"{pct}% SLA Violated 🔴"
    if pct >= 25:
        return "high",     "high-sla",  f"{pct}% SLA Violated"
    if pct >= 15:
        return "medium",   "med-sla",   f"{pct}% SLA Violated"
    return "ok",       "ok-sla",    f"{pct}% SLA Violated"


def _bar_color(i: int) -> str:
    colors = ["", "orange", "red", "teal", "blue", ""]
    return colors[i % len(colors)]


# ── BAR CHART HELPERS ─────────────────────────────────────────────────────────

def _bar_rows(items: list[tuple[str, int]], max_val: int, color: str = "") -> str:
    html = ""
    for label, count in items:
        pct = round(count / max_val * 100, 1) if max_val else 0
        color_class = f" {color}" if color else ""
        html += f"""
      <div class="bar-row">
        <div class="bar-label">{label}</div>
        <div class="bar-track"><div class="bar-fill{color_class}" style="width:{pct}%"></div></div>
        <div class="bar-count">{count}</div>
      </div>"""
    return html


# ── MODULE CARD BUILDER ───────────────────────────────────────────────────────

def _module_card(mod: str, data: dict, sla_info: dict, rca_breakdown: list) -> str:
    total    = sla_info.get("total", 0)
    violated = sla_info.get("violated", 0)
    pct      = sla_info.get("violation_pct", 0)
    card_cls, badge_cls, badge_label = _sla_risk(pct)

    warning_html = ""
    if pct >= 40:
        warning_html = f"""
      <div class="alert orange" style="margin-bottom:12px; font-size:11.5px;">
        <div class="alert-icon">⚠️</div>
        <div>This module has a <strong>critically high SLA violation rate</strong> — {violated} out of {total} tickets breached SLA this week.</div>
      </div>"""

    rca_rows = ""
    for item in rca_breakdown[:7]:
        rca_rows += f"""
          <li>
            <div class="rca-issue"><strong>{item['category']}</strong></div>
            <div class="rca-cnt">{item['count']} <span style="font-size:10px;color:#999">({item['pct']}%)</span></div>
          </li>"""

    return f"""
      <div class="module-card {card_cls}">
        <div class="module-header">
          <div>
            <div class="module-name">{mod}</div>
            <div class="module-meta">{total} tickets &nbsp;|&nbsp; {violated} SLA violations</div>
          </div>
          <div class="sla-badge {badge_cls}">{badge_label}</div>
        </div>
        {warning_html}
        <ul class="rca-list">{rca_rows}</ul>
      </div>"""


# ── RECURRING ISSUES ──────────────────────────────────────────────────────────

_RANK_COLORS = ["red", "red", "orange", "orange", "", "", "blue", "blue"]

def _recurring_cards(items: list[dict], total: int) -> str:
    html = ""
    for i, item in enumerate(items[:8]):
        color = _RANK_COLORS[i] if i < len(_RANK_COLORS) else ""
        rank  = f"#{i+1} This Week"
        pct   = round(item['count'] / total * 100, 1) if total else 0
        html += f"""
      <div class="issue-card {color}">
        <div class="issue-rank">{rank}</div>
        <div class="issue-title">{item['name']}</div>
        <div class="issue-count">{item['count']} <span class="issue-count-label">tickets ({pct}%)</span></div>
      </div>"""
    return html


# ── MAIN RENDER ───────────────────────────────────────────────────────────────

def render(data: dict) -> str:
    week          = data["week_label"]
    total         = data["total"]
    violated      = data["total_violated"]
    sla_pct       = data["overall_sla_pct"]
    tech_esc      = data["tech_escalations"]
    kg            = data["knowledge_gaps"]
    generated_at  = data["generated_at"]

    # Module distribution bars
    module_items = list(data["module_counts"].items())[:14]
    max_mod = module_items[0][1] if module_items else 1
    module_bars = _bar_rows(module_items, max_mod)

    # Bucket table rows
    bucket_rows = ""
    for btype, cnt in data["type_counts"].items():
        pct = round(cnt / total * 100, 1) if total else 0
        bucket_rows += f"<tr><td><strong>{btype}</strong></td><td><strong>{cnt}</strong></td><td class='pct'>{pct}%</td></tr>"

    # Module cards (top 8 modules)
    module_cards_html = ""
    top_modules = sorted(data["module_counts"].items(), key=lambda x: -x[1])[:8]
    for mod, _ in top_modules:
        sla_info = data["sla_by_module"].get(mod, {"total": 0, "violated": 0, "violation_pct": 0})
        rca_bdown = data["module_rca_breakdown"].get(mod, [])
        module_cards_html += _module_card(mod, data, sla_info, rca_bdown)

    # SLA table rows
    sla_rows = ""
    sla_sorted = sorted(data["sla_by_module"].items(), key=lambda x: -x[1]["violation_pct"])
    for mod, s in sla_sorted:
        pct = s["violation_pct"]
        if pct >= 40:
            risk = '<span style="color:var(--red);font-weight:700;">🔴 CRITICAL</span>'
        elif pct >= 25:
            risk = '<span style="color:var(--orange);font-weight:700;">🟠 HIGH</span>'
        elif pct >= 15:
            risk = '<span style="color:var(--yellow);font-weight:700;">🟡 ELEVATED</span>'
        else:
            risk = '<span style="color:var(--teal);">🟢 OK</span>'
        sla_rows += f"<tr><td><strong>{mod}</strong></td><td>{s['total']}</td><td>{s['violated']}</td><td><strong style='color:{'var(--red)' if pct>=25 else 'inherit'}'>{pct}%</strong></td><td>{risk}</td></tr>"

    # Overall row
    sla_rows += f"<tr style='background:#f0f4e8'><td><strong>OVERALL</strong></td><td><strong>{total}</strong></td><td><strong>{violated}</strong></td><td><strong>{sla_pct}%</strong></td><td>—</td></tr>"

    # Top brands bars
    brand_items = list(data["brand_counts"].items())[:12]
    max_brand = brand_items[0][1] if brand_items else 1
    brand_bars = _bar_rows(brand_items, max_brand)

    # Recurring issues cards
    recurring_cards = _recurring_cards(data["recurring"], total)

    # RCA overview bars
    rca_items = list(data["rca_counts"].items())[:10]
    max_rca = rca_items[0][1] if rca_items else 1
    rca_bars = _bar_rows(rca_items, max_rca, "blue")

    # KG by module bars
    kg_items = list(data["kg_by_module"].items())[:8]
    max_kg = kg_items[0][1] if kg_items else 1
    kg_bars = _bar_rows(kg_items, max_kg, "orange")

    sla_alert = ""
    if sla_pct >= 30:
        sla_alert = f'<div class="alert red"><div class="alert-icon">🔴</div><div><strong>SLA Alert:</strong> Overall SLA violation rate is <strong>{sla_pct}%</strong> this week — above the 22% historical average.</div></div>'
    elif sla_pct >= 20:
        sla_alert = f'<div class="alert orange"><div class="alert-icon">⚠️</div><div><strong>SLA Watch:</strong> Overall SLA violation rate is <strong>{sla_pct}%</strong> this week — close to the 22% historical average.</div></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LimeChat Support Dashboard — {week}</title>
{_css()}
</head>
<body>

<div class="header">
  <h1>🍋 LimeChat Support — Weekly Dashboard</h1>
  <div class="meta">
    Week: <span>{week}</span> &nbsp;|&nbsp;
    Tickets: <span>{total}</span> &nbsp;|&nbsp;
    Generated: <span>{generated_at}</span>
  </div>
</div>

<div class="container">

  <div class="summary-grid">
    <div class="stat-card"><div class="label">Total Tickets</div><div class="value">{total}</div><div class="sub">This week (7 days)</div></div>
    <div class="stat-card red"><div class="label">SLA Violated</div><div class="value">{violated}</div><div class="sub">{sla_pct}% of tickets</div></div>
    <div class="stat-card orange"><div class="label">Tech Escalations</div><div class="value">{tech_esc}</div><div class="sub">Tech Team Assistance Needed</div></div>
    <div class="stat-card blue"><div class="label">Knowledge Gaps</div><div class="value">{kg}</div><div class="sub">Product Knowledge Gap type</div></div>
  </div>

  {sla_alert}

  <div class="section">
    <div class="section-title">Module Distribution <span class="badge">{len(data['module_counts'])} modules</span></div>
    <div class="chart-box">{module_bars}</div>
  </div>

  <div class="section">
    <div class="section-title">Ticket Buckets (Type Classification)</div>
    <table class="bucket-table">
      <thead><tr><th>Bucket / Type</th><th>Count</th><th>% Share</th></tr></thead>
      <tbody>{bucket_rows}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Most Repeated Issues This Week <span class="badge">cross-module</span></div>
    <div class="top-issues-grid">{recurring_cards}</div>
  </div>

  <div class="section">
    <div class="section-title">Module-Level RCA Breakdown</div>
    <div class="module-grid">{module_cards_html}</div>
  </div>

  <div class="section">
    <div class="section-title">RCA Category Overview</div>
    <div class="chart-box">{rca_bars}</div>
  </div>

  <div class="section">
    <div class="section-title">SLA Performance by Module</div>
    <table class="bucket-table">
      <thead><tr><th>Module</th><th>Total</th><th>Violated</th><th>Rate</th><th>Risk</th></tr></thead>
      <tbody>{sla_rows}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">Top Brands by Ticket Volume</div>
    <div class="chart-box">{brand_bars}</div>
  </div>

  <div class="section">
    <div class="section-title">Knowledge Gap Tickets by Module <span class="badge">{kg} total</span></div>
    {"<div class='alert lime'><div class='alert-icon'>💡</div><div>These are avoidable tickets — training/documentation opportunities.</div></div>" if kg > 0 else ""}
    <div class="chart-box">{kg_bars if kg_bars.strip() else "<p style='padding:12px;color:#999;'>No knowledge gap tickets this week 🎉</p>"}</div>
  </div>

  <div class="footer">
    LimeChat Internal Support Analysis &nbsp;|&nbsp; {week} &nbsp;|&nbsp; {total} tickets &nbsp;|&nbsp; support@limechat.ai
  </div>

</div>
</body>
</html>"""


def _css() -> str:
    return """<style>
  :root {
    --lime: #7EC820; --lime-dark: #5a9c14; --lime-light: #e8f5d0; --lime-pale: #f4fbea;
    --dark: #1a1a2e; --mid: #2d2d44; --text: #2c2c2c; --muted: #666;
    --border: #dde8c8; --red: #e53e3e; --orange: #dd6b20; --yellow: #d69e2e;
    --blue: #3182ce; --teal: #2c7a7b; --white: #fff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4e8; color: var(--text); font-size: 14px; }
  .header { background: var(--dark); color: #fff; padding: 28px 40px 22px; border-bottom: 4px solid var(--lime); }
  .header h1 { font-size: 22px; font-weight: 700; }
  .header .meta { font-size: 12px; color: #aaa; margin-top: 6px; }
  .header .meta span { color: var(--lime); font-weight: 600; }
  .container { max-width: 1200px; margin: 0 auto; padding: 28px 24px 60px; }
  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
  .stat-card { background: var(--white); border-radius: 10px; padding: 18px 20px; border-left: 4px solid var(--lime); box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
  .stat-card .label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 6px; }
  .stat-card .value { font-size: 28px; font-weight: 700; color: var(--dark); }
  .stat-card .sub { font-size: 11px; color: var(--muted); margin-top: 4px; }
  .stat-card.red { border-left-color: var(--red); }
  .stat-card.orange { border-left-color: var(--orange); }
  .stat-card.blue { border-left-color: var(--blue); }
  .section { margin-bottom: 32px; }
  .section-title { font-size: 15px; font-weight: 700; color: var(--dark); border-bottom: 2px solid var(--lime); padding-bottom: 6px; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
  .section-title .badge { background: var(--lime); color: #fff; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
  .chart-box { background: var(--white); border-radius: 10px; padding: 20px 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
  .module-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .module-card { background: var(--white); border-radius: 10px; padding: 18px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-top: 3px solid var(--lime); }
  .module-card.critical { border-top-color: var(--red); }
  .module-card.high { border-top-color: var(--orange); }
  .module-card.medium { border-top-color: var(--yellow); }
  .module-card.ok { border-top-color: var(--teal); }
  .module-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
  .module-name { font-size: 13px; font-weight: 700; color: var(--dark); }
  .module-meta { font-size: 11px; color: var(--muted); margin-top: 2px; }
  .sla-badge { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; white-space: nowrap; }
  .sla-badge.critical { background: #fff0f0; color: var(--red); border: 1px solid #fca5a5; }
  .sla-badge.high-sla { background: #fff7ed; color: var(--orange); border: 1px solid #fdba74; }
  .sla-badge.med-sla { background: #fffbeb; color: var(--yellow); border: 1px solid #fcd34d; }
  .sla-badge.ok-sla { background: #f0fdf4; color: var(--teal); border: 1px solid #86efac; }
  .rca-list { list-style: none; margin-top: 10px; }
  .rca-list li { display: flex; justify-content: space-between; align-items: flex-start; padding: 7px 0; border-bottom: 1px dashed #eee; gap: 8px; }
  .rca-list li:last-child { border-bottom: none; }
  .rca-issue { flex: 1; font-size: 12px; color: var(--text); }
  .rca-cnt { font-size: 12px; font-weight: 700; color: var(--lime-dark); min-width: 40px; text-align: right; }
  .bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 7px; }
  .bar-label { font-size: 12px; color: var(--text); width: 220px; flex-shrink: 0; line-height: 1.3; }
  .bar-track { flex: 1; background: #edf2e8; border-radius: 4px; height: 14px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; background: var(--lime); }
  .bar-fill.red { background: var(--red); }
  .bar-fill.orange { background: var(--orange); }
  .bar-fill.blue { background: var(--blue); }
  .bar-fill.teal { background: var(--teal); }
  .bar-count { font-size: 12px; font-weight: 600; color: var(--dark); min-width: 30px; text-align: right; }
  .bucket-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  .bucket-table th { background: var(--dark); color: #fff; padding: 9px 12px; text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
  .bucket-table td { padding: 8px 12px; border-bottom: 1px solid #eee; }
  .bucket-table tr:nth-child(even) td { background: #f8fdf2; }
  .bucket-table .pct { color: var(--muted); font-size: 11px; }
  .top-issues-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
  .issue-card { background: var(--white); border-radius: 10px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border-left: 3px solid var(--lime); }
  .issue-card.red { border-left-color: var(--red); }
  .issue-card.orange { border-left-color: var(--orange); }
  .issue-card.blue { border-left-color: var(--blue); }
  .issue-rank { font-size: 10px; font-weight: 700; color: var(--lime-dark); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 5px; }
  .issue-title { font-size: 12px; font-weight: 700; color: var(--dark); margin-bottom: 6px; line-height: 1.3; }
  .issue-count { font-size: 20px; font-weight: 800; color: var(--lime-dark); }
  .issue-count-label { font-size: 11px; color: var(--muted); font-weight: 400; }
  .alert { border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; font-size: 12.5px; display: flex; gap: 10px; align-items: flex-start; }
  .alert.red { background: #fff0f0; border: 1px solid #fca5a5; color: #c53030; }
  .alert.orange { background: #fff7ed; border: 1px solid #fdba74; color: #9c4221; }
  .alert.lime { background: var(--lime-pale); border: 1px solid var(--border); color: var(--lime-dark); }
  .alert-icon { font-size: 16px; }
  .footer { text-align: center; font-size: 11px; color: var(--muted); padding-top: 20px; border-top: 1px solid var(--border); margin-top: 40px; }
</style>"""
