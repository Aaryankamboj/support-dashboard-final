"""
fetch_tickets.py
Pulls last 7 days of tickets from Freshdesk API.
Handles pagination automatically (Freshdesk returns 30 per page by default, max 100).
"""

import os
import requests
import json
from datetime import datetime, timedelta, timezone


FRESHDESK_DOMAIN = os.environ.get("FRESHDESK_DOMAIN", "limechatai")   # just the subdomain
FRESHDESK_API_KEY = os.environ["FRESHDESK_API_KEY"]
BASE_URL = f"https://{FRESHDESK_DOMAIN}.freshdesk.com/api/v2"


def fetch_tickets_last_7_days() -> list[dict]:
    """Fetch all tickets created in the last 7 days via Freshdesk /search/tickets endpoint."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tickets = []
    page = 1

    print(f"Fetching tickets created since {since} ...")

    while True:
        url = f"{BASE_URL}/tickets"
        params = {
            "updated_since": since,
            "per_page": 100,
            "page": page,
            "include": "stats",               # includes resolved_at etc.
            "order_by": "created_at",
            "order_type": "desc",
        }
        resp = requests.get(
            url,
            params=params,
            auth=(FRESHDESK_API_KEY, "X"),    # Freshdesk uses API key as basic auth username
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        tickets.extend(batch)
        print(f"  Page {page}: fetched {len(batch)} tickets (total so far: {len(tickets)})")
        if len(batch) < 100:
            break
        page += 1

    # Filter strictly to created_at within last 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    filtered = []
    for t in tickets:
        created_str = t.get("created_at", "")
        if created_str:
            created_dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            if created_dt >= cutoff:
                filtered.append(t)

    print(f"Tickets after date filter: {len(filtered)}")
    return filtered


def normalize_ticket(raw: dict) -> dict:
    """Map Freshdesk API response fields to the same keys used in our CSV analysis."""
    cf = raw.get("custom_fields", {}) or {}

    # Freshdesk custom field names (snake_case of the column headers you see in the CSV)
    # These may differ slightly per account — adjust if needed
    return {
        "Ticket ID":            str(raw.get("id", "")),
        "Subject":              raw.get("subject", ""),
        "Status":               _status_label(raw.get("status")),
        "Priority":             _priority_label(raw.get("priority")),
        "Type":                 raw.get("type", "") or "",
        "Agent":                _agent_name(raw),
        "Created time":         raw.get("created_at", ""),
        "Resolved time":        (raw.get("stats") or {}).get("resolved_at") or raw.get("resolved_at", ""),
        "Resolution status":    _resolution_status(raw),
        "Tags":                 ", ".join(raw.get("tags", [])),
        "Product Module":       cf.get("cf_product_module", "") or "",
        "RCA":                  cf.get("cf_rca", "") or "",
        "Brand Name":           cf.get("cf_brand_name", "") or "",
        "Issue Brief - Internal": cf.get("cf_issue_brief_internal", "") or "",
        "Knowledge Gap":        cf.get("cf_knowledge_gap", "") or "",
        "Engineer":             cf.get("cf_engineer", "") or "",
        # Resolution time in hours
        "Resolution time (in hrs)": _resolution_hours(raw),
    }


def _status_label(code) -> str:
    return {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}.get(code, str(code or ""))


def _priority_label(code) -> str:
    return {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}.get(code, str(code or ""))


def _agent_name(raw: dict) -> str:
    responder = raw.get("responder_id")
    return str(responder) if responder else ""


def _resolution_status(raw: dict) -> str:
    """Simplified: compare resolved_at to due_by."""
    stats = raw.get("stats") or {}
    resolved_at = stats.get("resolved_at") or raw.get("resolved_at")
    due_by = raw.get("due_by")
    if not resolved_at:
        return "Unresolved"
    if not due_by:
        return "Within SLA"
    try:
        r = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        d = datetime.fromisoformat(due_by.replace("Z", "+00:00"))
        return "Within SLA" if r <= d else "SLA Violated"
    except Exception:
        return "Unknown"


def _resolution_hours(raw: dict) -> str:
    stats = raw.get("stats") or {}
    resolved_at = stats.get("resolved_at") or raw.get("resolved_at")
    created_at = raw.get("created_at")
    if not resolved_at or not created_at:
        return ""
    try:
        r = datetime.fromisoformat(resolved_at.replace("Z", "+00:00"))
        c = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return f"{round((r - c).total_seconds() / 3600, 2)}"
    except Exception:
        return ""


def get_normalized_tickets() -> list[dict]:
    raw = fetch_tickets_last_7_days()
    normalized = [normalize_ticket(t) for t in raw]
    print(f"Normalized {len(normalized)} tickets.")
    return normalized
