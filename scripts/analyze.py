"""
analyze.py
Categorizes tickets into RCA buckets, computes module/type/SLA metrics.
Returns structured data dict ready for dashboard generation.
"""

import collections
from datetime import datetime, timezone


# ── RCA KEYWORD CLASSIFIER ────────────────────────────────────────────────────

def classify_rca(rca_text: str, subject_text: str) -> str:
    text = (rca_text + " " + subject_text).lower()

    if any(k in text for k in ["mailgun", "email not forward", "email miss", "inbound email", "email not sync"]):
        return "Mailgun / Email Inbound Failure"
    if any(k in text for k in ["csat", "survey not", "survey trigger", "bot csat"]):
        return "CSAT Not Triggering / Inconsistent"
    if any(k in text for k in ["assign", "assignment rule", "not assigned", "ticket assign delay"]):
        return "Ticket/Chat Assignment Delay or Failure"
    if any(k in text for k in ["karix", "netcore", "gupshup", "360dialog", "bsp", "delivery fail",
                                 "not delivered", "delivery error", "downtime", "error code 8006",
                                 "provider", "whatsapp account level"]):
        return "BSP/Provider Delivery Issue"
    if any(k in text for k in ["duplicate ticket", "duplicate conversation", "duplicate message"]):
        return "Duplicate Ticket/Message"
    if any(k in text for k in ["label", "tag ", "tagging"]):
        return "Labels/Tags Issue"
    if any(k in text for k in ["report", "mismatch", "discrepancy", "metric", "analytics count",
                                 "data mismatch", "ui data", "dashboard not reflect"]):
        return "Report/Analytics Data Mismatch"
    if any(k in text for k in ["knowledge gap", "feature not", "not supported", "feature request"]):
        return "Product Knowledge Gap / Feature Not Available"
    if any(k in text for k in ["api", "webhook", "shopify", "salesforce", "exotel", "razorpay",
                                 "integration", "external", "400 bad request", "external api"]):
        return "Integration/API/Webhook Issue"
    if any(k in text for k in ["broadcast", "campaign", "template", "outbound message"]):
        return "Broadcast/Campaign/Template Issue"
    if any(k in text for k in ["bot", "flow", "automation", "flow not trigger", "not triggered"]):
        return "Bot/Flow/Automation Issue"
    if any(k in text for k in ["account", "login", "activation", "password", "access",
                                 "email suppres", "user creat"]):
        return "Account/Access/Login Issue"
    if any(k in text for k in ["misconfigur", "wrong setting", "wrong config", "incorrect config",
                                 "config", "admin updated", "client error"]):
        return "Misconfiguration by Client/Admin"
    if any(k in text for k in ["payment", "invoice", "billing"]):
        return "Billing/Payment"
    return "Other"


# ── MAIN ANALYSIS FUNCTION ────────────────────────────────────────────────────

def analyze(tickets: list[dict]) -> dict:
    """
    Returns a structured dict with all metrics needed by generate_html.py.
    """
    total = len(tickets)
    week_label = _week_label()

    # ── Module counts
    module_counts = collections.Counter(
        t.get("Product Module", "").strip() or "Unclassified" for t in tickets
    )

    # ── Type (bucket) counts
    type_counts = collections.Counter(
        t.get("Type", "").strip() or "Unclassified" for t in tickets
    )

    # ── SLA violation per module
    sla_by_module = {}
    for mod in module_counts:
        mod_tickets = [t for t in tickets if (t.get("Product Module", "").strip() or "Unclassified") == mod]
        violated = sum(1 for t in mod_tickets if "violated" in t.get("Resolution status", "").lower())
        within   = sum(1 for t in mod_tickets if "within sla" in t.get("Resolution status", "").lower())
        sla_by_module[mod] = {
            "total": len(mod_tickets),
            "violated": violated,
            "within": within,
            "violation_pct": round(violated / len(mod_tickets) * 100, 1) if mod_tickets else 0,
        }

    # ── Overall SLA
    total_violated = sum(1 for t in tickets if "violated" in t.get("Resolution status", "").lower())
    overall_sla_pct = round(total_violated / total * 100, 1) if total else 0

    # ── RCA classification per ticket
    for t in tickets:
        t["_rca_category"] = classify_rca(t.get("RCA", ""), t.get("Subject", ""))

    # ── Overall RCA distribution
    rca_counts = collections.Counter(t["_rca_category"] for t in tickets)

    # ── Per-module RCA breakdown (top 6 per module)
    module_rca_breakdown = {}
    for mod in module_counts:
        mod_tickets = [t for t in tickets if (t.get("Product Module", "").strip() or "Unclassified") == mod]
        rca_in_mod = collections.Counter(t["_rca_category"] for t in mod_tickets)
        module_rca_breakdown[mod] = [
            {"category": cat, "count": cnt,
             "pct": round(cnt / len(mod_tickets) * 100, 1)}
            for cat, cnt in rca_in_mod.most_common(6)
        ]

    # ── Top brands by ticket volume
    brand_counts = collections.Counter(
        t.get("Brand Name", "").strip() for t in tickets if t.get("Brand Name", "").strip()
    )

    # ── Knowledge gap by module
    kg_tickets = [t for t in tickets if t.get("Type", "").strip() == "Product Knowledge Gap"]
    kg_by_module = collections.Counter(
        t.get("Product Module", "").strip() or "Unclassified" for t in kg_tickets
    )

    # ── Specific recurring patterns (cross-module)
    recurring = _recurring_patterns(tickets)

    # ── Tech escalation count
    tech_escalations = sum(1 for t in tickets if t.get("Type", "").strip() == "Tech Team Assistance Needed")

    return {
        "week_label":           week_label,
        "total":                total,
        "total_violated":       total_violated,
        "overall_sla_pct":      overall_sla_pct,
        "tech_escalations":     tech_escalations,
        "knowledge_gaps":       len(kg_tickets),
        "module_counts":        dict(module_counts.most_common()),
        "type_counts":          dict(type_counts.most_common()),
        "sla_by_module":        sla_by_module,
        "rca_counts":           dict(rca_counts.most_common()),
        "module_rca_breakdown": module_rca_breakdown,
        "brand_counts":         dict(brand_counts.most_common(15)),
        "kg_by_module":         dict(kg_by_module.most_common()),
        "recurring":            recurring,
        "generated_at":         datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def _week_label() -> str:
    from datetime import timedelta
    end   = datetime.now(timezone.utc).date()
    start = end - timedelta(days=6)
    return f"{start.strftime('%b %d')} – {end.strftime('%b %d, %Y')}"


def _recurring_patterns(tickets: list[dict]) -> list[dict]:
    """Count specific high-signal recurring issue patterns."""
    patterns = [
        {
            "name": "Bot / Flow / Automation Failures",
            "keywords_rca":  ["bot", "flow", "automation"],
            "keywords_subj": ["flow not", "automation not", "bot issue", "bot fail"],
        },
        {
            "name": "BSP / Provider Delivery Failures",
            "keywords_rca":  ["karix", "netcore", "gupshup", "360dialog", "delivery fail",
                              "not delivered", "error code", "downtime", "provider"],
            "keywords_subj": [],
        },
        {
            "name": "Report / Analytics Data Mismatch",
            "keywords_rca":  ["mismatch", "discrepancy", "not match", "logic inconsistency",
                              "different count"],
            "keywords_subj": ["mismatch", "discrepancy", "report issue", "analytics"],
        },
        {
            "name": "Integration / API / Webhook Failures",
            "keywords_rca":  ["api", "webhook", "shopify", "salesforce", "integration",
                              "400 bad request", "external api"],
            "keywords_subj": ["integration", "webhook", "api", "shopify"],
        },
        {
            "name": "Template Issues (Approval / Migration / Delivery)",
            "keywords_rca":  ["template", "in review", "template not approv"],
            "keywords_subj": ["template", "in review"],
        },
        {
            "name": "CSAT Not Triggering / Inconsistent",
            "keywords_rca":  ["csat", "survey not", "csat trigger"],
            "keywords_subj": ["csat", "survey"],
        },
        {
            "name": "Ticket / Chat Assignment Delays",
            "keywords_rca":  ["assign", "assignment rule", "not assigned"],
            "keywords_subj": ["assign", "assignment"],
        },
        {
            "name": "Mailgun Email Inbound Failures",
            "keywords_rca":  ["mailgun"],
            "keywords_subj": ["email miss", "email not sync", "email thread miss"],
        },
    ]

    results = []
    for p in patterns:
        count = 0
        for t in tickets:
            rca  = t.get("RCA", "").lower()
            subj = t.get("Subject", "").lower()
            hit_rca  = any(k in rca  for k in p["keywords_rca"])
            hit_subj = any(k in subj for k in p.get("keywords_subj", []))
            if hit_rca or hit_subj:
                count += 1
        results.append({"name": p["name"], "count": count})

    return sorted(results, key=lambda x: -x["count"])
