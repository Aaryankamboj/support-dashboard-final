# 🍋 LimeChat Weekly Support Dashboard — Setup Guide

Zero-infra, fully automated. Every Monday at 7 AM IST, GitHub fetches your
Freshdesk tickets, builds the dashboard, publishes it to GitHub Pages, and
emails you the link. Nothing to maintain.

---

## What you need before starting

| Item | Where to get it |
|------|----------------|
| GitHub account (free) | github.com |
| Freshdesk API key | Freshdesk → Profile Settings → API Key |
| Gmail App Password | Google Account → Security → App Passwords |

---

## Step 1 — Create the GitHub repository

1. Go to **github.com → New repository**
2. Name it `support-dashboard`
3. Set visibility: **Public** ← required for free GitHub Pages
4. Click **Create repository**

---

## Step 2 — Upload the project files

Upload all files from this folder to the new repo.  
The structure must look exactly like this:

```
support-dashboard/
├── .github/
│   └── workflows/
│       └── weekly_dashboard.yml
├── docs/
│   └── index.html          ← placeholder, gets overwritten each Monday
├── scripts/
│   ├── fetch_tickets.py
│   ├── analyze.py
│   ├── generate_html.py
│   └── send_email.py
├── run.py
└── requirements.txt
```

**Quickest way:** Use GitHub's "Upload files" button and drag the entire folder.

---

## Step 3 — Enable GitHub Pages

1. In your repo → **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` &nbsp;|&nbsp; Folder: `/docs`
4. Click **Save**

Your public dashboard URL will be:
```
https://<your-github-username>.github.io/support-dashboard/
```

---

## Step 4 — Add secrets (one-time)

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add each secret below:

| Secret name | Value | Example |
|-------------|-------|---------|
| `FRESHDESK_API_KEY` | Your Freshdesk API key | `abc123xyz...` |
| `FRESHDESK_DOMAIN` | Your Freshdesk subdomain | `limechatai` |
| `SMTP_FROM` | Gmail address to send FROM | `support@limechat.ai` |
| `SMTP_TO` | Recipient email(s), comma-separated | `aaryan@limechat.ai,team@limechat.ai` |
| `SMTP_PASSWORD` | Gmail **App Password** (not your login password) | `abcd efgh ijkl mnop` |

> **How to get a Gmail App Password:**
> Google Account → Security → 2-Step Verification must be ON →
> then Security → App Passwords → Select app: Mail → Generate

---

## Step 5 — Run it manually to test

1. Go to your repo → **Actions** tab
2. Click **Weekly Support Dashboard** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Watch the logs — it should complete in ~1 minute
5. Visit your GitHub Pages URL to see the live dashboard
6. Check your inbox for the email

---

## Step 6 — You're done 🎉

From now on, every **Monday at 7:00 AM IST** the pipeline runs automatically:

```
Freshdesk API → analyze.py → docs/index.html → GitHub Pages → email you
```

The dashboard URL never changes — you can bookmark it and share it freely.

---

## Customizing Freshdesk custom field names

Your Freshdesk custom fields may have different internal names than the defaults
in `scripts/fetch_tickets.py`. To check your actual field names:

```bash
curl -u YOUR_API_KEY:X \
  "https://limechatai.freshdesk.com/api/v2/tickets?per_page=1&include=stats" \
  | python3 -m json.tool | grep -i "cf_"
```

Then update the `normalize_ticket()` function in `scripts/fetch_tickets.py`
to match the field names returned.

Common field name patterns in Freshdesk:
- `cf_product_module`
- `cf_rca`
- `cf_brand_name`
- `cf_issue_brief_internal`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No tickets in dashboard | Check `FRESHDESK_API_KEY` and `FRESHDESK_DOMAIN` secrets |
| Email not arriving | Use Gmail App Password (not login password); check spam |
| GitHub Pages shows 404 | Ensure `/docs` folder is selected in Pages settings |
| Action fails with permission error | Repo → Settings → Actions → General → Workflow permissions → Read and write |

---

## File overview

| File | Purpose |
|------|---------|
| `run.py` | Main pipeline — fetch → analyze → generate → email |
| `scripts/fetch_tickets.py` | Freshdesk API client, pagination, field normalization |
| `scripts/analyze.py` | RCA classification, SLA metrics, recurring pattern detection |
| `scripts/generate_html.py` | Full HTML dashboard renderer |
| `scripts/send_email.py` | Gmail SMTP email with inline stats |
| `.github/workflows/weekly_dashboard.yml` | GitHub Actions cron job (Mon 7 AM IST) |
| `docs/index.html` | Auto-generated dashboard (overwritten each week) |
| `requirements.txt` | Python dependencies (`requests` only) |
