"""
send_email.py
Sends the weekly dashboard notification email with the GitHub Pages link.
Uses Gmail SMTP (or any SMTP server configured via environment variables).
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_weekly_email(week_label: str, dashboard_url: str, stats: dict) -> None:
    """
    Send a clean HTML email with dashboard link and key weekly stats.

    Required env vars:
      SMTP_FROM      — sender address (e.g. support@limechat.ai)
      SMTP_TO        — recipient(s), comma-separated
      SMTP_PASSWORD  — app password for the sender account
      SMTP_HOST      — SMTP server host (default: smtp.gmail.com)
      SMTP_PORT      — SMTP port (default: 587)
    """
    smtp_from  = os.environ["SMTP_FROM"]
    smtp_to    = [e.strip() for e in os.environ["SMTP_TO"].split(",")]
    smtp_pass  = os.environ["SMTP_PASSWORD"]
    smtp_host  = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port  = int(os.environ.get("SMTP_PORT", 587))

    total     = stats.get("total", 0)
    violated  = stats.get("total_violated", 0)
    sla_pct   = stats.get("overall_sla_pct", 0)
    tech_esc  = stats.get("tech_escalations", 0)
    kg        = stats.get("knowledge_gaps", 0)

    # Build key metrics rows
    top_module = next(iter(stats.get("module_counts", {}).items()), ("—", 0))
    top_issue  = stats["recurring"][0]["name"] if stats.get("recurring") else "—"
    top_issue_cnt = stats["recurring"][0]["count"] if stats.get("recurring") else 0

    sla_color = "#e53e3e" if sla_pct >= 25 else "#dd6b20" if sla_pct >= 15 else "#2c7a7b"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4e8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4e8;padding:32px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,0.08);">

      <!-- Header -->
      <tr>
        <td style="background:#1a1a2e;padding:24px 32px;border-bottom:4px solid #7EC820;">
          <div style="font-size:20px;font-weight:700;color:#fff;">🍋 LimeChat Weekly Support Dashboard</div>
          <div style="font-size:12px;color:#aaa;margin-top:6px;">Week of <span style="color:#7EC820;font-weight:600;">{week_label}</span></div>
        </td>
      </tr>

      <!-- Intro -->
      <tr>
        <td style="padding:24px 32px 8px;">
          <p style="font-size:14px;color:#444;margin:0;">Hi team 👋 — your weekly support ticket analysis is ready. Here's a quick snapshot:</p>
        </td>
      </tr>

      <!-- Stats Grid -->
      <tr>
        <td style="padding:16px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td width="25%" style="padding:4px;">
                <div style="background:#f8fdf2;border-left:4px solid #7EC820;border-radius:8px;padding:14px 16px;">
                  <div style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:0.5px;">Total Tickets</div>
                  <div style="font-size:26px;font-weight:800;color:#1a1a2e;">{total}</div>
                </div>
              </td>
              <td width="25%" style="padding:4px;">
                <div style="background:#fff0f0;border-left:4px solid #e53e3e;border-radius:8px;padding:14px 16px;">
                  <div style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:0.5px;">SLA Violated</div>
                  <div style="font-size:26px;font-weight:800;color:{sla_color};">{violated}</div>
                  <div style="font-size:11px;color:#999;">{sla_pct}% of tickets</div>
                </div>
              </td>
              <td width="25%" style="padding:4px;">
                <div style="background:#fff7ed;border-left:4px solid #dd6b20;border-radius:8px;padding:14px 16px;">
                  <div style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:0.5px;">Tech Escalations</div>
                  <div style="font-size:26px;font-weight:800;color:#dd6b20;">{tech_esc}</div>
                </div>
              </td>
              <td width="25%" style="padding:4px;">
                <div style="background:#eff6ff;border-left:4px solid #3182ce;border-radius:8px;padding:14px 16px;">
                  <div style="font-size:10px;color:#666;text-transform:uppercase;letter-spacing:0.5px;">Knowledge Gaps</div>
                  <div style="font-size:26px;font-weight:800;color:#3182ce;">{kg}</div>
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- Key Highlights -->
      <tr>
        <td style="padding:8px 32px 16px;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fdf2;border-radius:8px;padding:16px;">
            <tr>
              <td style="padding:6px 12px;font-size:13px;">
                📦 <strong>Top module:</strong> {top_module[0]} ({top_module[1]} tickets)
              </td>
            </tr>
            <tr>
              <td style="padding:6px 12px;font-size:13px;">
                🔁 <strong>Most repeated issue:</strong> {top_issue} ({top_issue_cnt} tickets)
              </td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- CTA Button -->
      <tr>
        <td align="center" style="padding:20px 32px 32px;">
          <a href="{dashboard_url}"
             style="display:inline-block;background:#7EC820;color:#fff;font-size:15px;font-weight:700;
                    padding:14px 36px;border-radius:8px;text-decoration:none;letter-spacing:0.3px;">
            📊 Open Full Dashboard →
          </a>
          <div style="margin-top:12px;font-size:11px;color:#999;">
            Public link: <a href="{dashboard_url}" style="color:#7EC820;">{dashboard_url}</a>
          </div>
        </td>
      </tr>

      <!-- Footer -->
      <tr>
        <td style="background:#f8fdf2;padding:14px 32px;text-align:center;border-top:1px solid #dde8c8;">
          <p style="font-size:11px;color:#999;margin:0;">
            LimeChat Support Ops &nbsp;·&nbsp; Auto-generated every Monday &nbsp;·&nbsp; support@limechat.ai
          </p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📊 Weekly Support Dashboard — {week_label}"
    msg["From"]    = smtp_from
    msg["To"]      = ", ".join(smtp_to)
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_from, smtp_pass)
        server.sendmail(smtp_from, smtp_to, msg.as_string())

    print(f"Email sent to: {', '.join(smtp_to)}")
