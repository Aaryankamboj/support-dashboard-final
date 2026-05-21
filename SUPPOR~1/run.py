#!/usr/bin/env python3
"""
run.py — Main entry point for the weekly support dashboard pipeline.

Steps:
  1. Fetch last 7 days of tickets from Freshdesk API
  2. Analyze & categorize into RCA buckets
  3. Generate HTML dashboard → docs/index.html  (GitHub Pages serves from /docs)
  4. Send email notification with public dashboard URL

Run locally:
  FRESHDESK_API_KEY=xxx SMTP_FROM=... SMTP_TO=... SMTP_PASSWORD=... python run.py

GitHub Actions runs this every Monday at 7:00 AM IST (1:30 AM UTC).
"""

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))

from fetch_tickets import get_normalized_tickets
from analyze import analyze
from generate_html import render
from send_email import send_weekly_email


# ── CONFIG ────────────────────────────────────────────────────────────────────

GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER", "your-github-username")
GITHUB_REPO_NAME  = os.environ.get("GITHUB_REPO_NAME",  "support-dashboard")
DASHBOARD_URL     = f"https://{GITHUB_REPO_OWNER}.github.io/{GITHUB_REPO_NAME}/"

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "docs", "index.html")


# ── PIPELINE ──────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("LimeChat Weekly Support Dashboard — Pipeline Start")
    print("=" * 60)

    # Step 1: Fetch
    print("\n[1/4] Fetching tickets from Freshdesk...")
    tickets = get_normalized_tickets()
    if not tickets:
        print("⚠️  No tickets found for the last 7 days. Generating empty dashboard.")

    # Step 2: Analyze
    print(f"\n[2/4] Analyzing {len(tickets)} tickets...")
    data = analyze(tickets)
    print(f"  Total: {data['total']} | SLA Violated: {data['total_violated']} ({data['overall_sla_pct']}%)")
    print(f"  Top module: {next(iter(data['module_counts'].items()), ('—', 0))}")
    print(f"  Top recurring issue: {data['recurring'][0]['name'] if data['recurring'] else '—'}")

    # Step 3: Generate HTML
    print(f"\n[3/4] Generating HTML dashboard → {OUTPUT_PATH}")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    html = render(data)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Dashboard written ({len(html):,} bytes)")

    # Step 4: Send email
    print(f"\n[4/4] Sending email notification...")
    print(f"  Dashboard URL: {DASHBOARD_URL}")
    try:
        send_weekly_email(
            week_label    = data["week_label"],
            dashboard_url = DASHBOARD_URL,
            stats         = data,
        )
    except Exception as e:
        print(f"  ⚠️  Email failed: {e}")
        print("  (Dashboard was still generated — check GitHub Pages URL)")

    print("\n✅ Pipeline complete!")
    print(f"   Public dashboard: {DASHBOARD_URL}")


if __name__ == "__main__":
    main()
