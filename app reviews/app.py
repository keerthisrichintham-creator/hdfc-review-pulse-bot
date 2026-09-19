"""
HDFC MFOnline Investors — App Review Insights Analyser (LIP 5)
Problem Discovery layer that feeds the LIP-4 RAG Chatbot (Solution layer).
"""

import io
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                 Spacer, Table, TableStyle)

LIP4_URL = "https://hdfc-bot.streamlit.app"
REQUIRED_COLUMNS = ["date", "rating", "title", "text", "source"]

# ----------------------------------------------------------------------------
# Theme definitions (fixed — max 5, do not exceed)
# ----------------------------------------------------------------------------
THEME_DEFS = {
    "NAV & Portfolio Display": {
        "keywords": [
            "nav", "xirr", "portfolio", "rounded", "exact value", "exact amount",
            "units not visible", "units", "holdings value", "portfolio value",
        ],
        "description": "NAV date/value missing, portfolio amount rounded instead of exact, "
                        "XIRR per scheme missing, units not visible after update.",
        "action": "Product P0: Restore NAV Dashboard — show NAV Date, NAV Value, "
                  "Exact Amount, Units, and XIRR per scheme.",
    },
    "Login & Authentication": {
        "keywords": [
            "otp", "login", "logout", "account blocked", "blocked after", "session",
            "auto-logout", "auto logout", "network error", "authentication",
        ],
        "description": "OTP not received, account blocked after 3 attempts, logout shows "
                        "network error loop, session expired, auto-logout.",
        "action": "Engineering P1: Fix session persistence bug causing logout to network "
                  "error loop. Add retry logic, proper error message, and auto-unblock "
                  "after 30 minutes.",
    },
    "Payments & Transactions": {
        "keywords": [
            "sip", "payment", "redemption", "deducted", "transaction", "redeem",
        ],
        "description": "SIP payment deducted but not reflecting in app, redemption stuck "
                        "for more than 3 days, payment failed.",
        "action": "Engineering P0: Add real-time reconciliation for SIP and redemption "
                  "status so deducted payments reflect within minutes, not days.",
    },
    "Statements & Access": {
        "keywords": [
            "statement", "capital gain", "password", "download",
        ],
        "description": "Unable to download capital gain statement, statement password "
                        "not working, monthly statement fails.",
        "action": "Engineering P1: Fix capital gain statement generation and clearly "
                  "display the required password format on screen.",
    },
    "App Performance": {
        "keywords": [
            "slow", "30 seconds", "internal server error", "crash", "freeze", "server error",
        ],
        "description": "App is very slow, takes 30 seconds to open, internal server "
                        "error, crash.",
        "action": "Engineering P1: Profile and optimize portfolio/holdings load time; "
                  "add crash reporting and alerting.",
    },
}
THEME_ORDER = list(THEME_DEFS.keys())

# ----------------------------------------------------------------------------
# PII scrub — safety net in case an uploaded file still has identifiers
# ----------------------------------------------------------------------------
EMAIL_RE = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
PHONE_RE = re.compile(r"\b\d{10}\b")
HANDLE_RE = re.compile(r"@\w+")


def scrub_pii(text: str) -> str:
    if not isinstance(text, str):
        return text
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = PHONE_RE.sub("[redacted-number]", text)
    text = HANDLE_RE.sub("[redacted-handle]", text)
    return text


def classify_theme(row_text: str) -> str:
    text = row_text.lower()
    scores = {}
    for theme, cfg in THEME_DEFS.items():
        scores[theme] = sum(1 for kw in cfg["keywords"] if kw in text)
    best_theme = max(scores, key=scores.get)
    if scores[best_theme] == 0:
        return "App Performance"  # fallback bucket
    return best_theme


@st.cache_data
def load_sample_data() -> pd.DataFrame:
    # Small, self-contained sample so the app works before any upload.
    import random
    random.seed(42)
    from datetime import date, timedelta

    start = date(2026, 6, 28)
    end = date(2026, 9, 19)
    span = (end - start).days

    pools = {
        "NAV & Portfolio Display": [
            "NAV not showing anywhere after new update. Cannot see today's NAV or units.",
            "My portfolio shows 2.19L but I need exact amount with decimals for tracking.",
            "Earlier we could see XIRR per scheme now gone. Please bring back.",
            "NAV not updated even after 2 days. Shows old NAV date.",
        ],
        "Login & Authentication": [
            "Every time I logout it says network error. OTP not received. Login loop.",
            "Account blocked after 3 wrong attempts, no way to unblock for 24 hours.",
            "After login it logs out automatically. Cannot access holdings.",
        ],
        "Payments & Transactions": [
            "SIP payment deducted but not showing in app. Very frustrating.",
            "Redemption request placed 3 days back still not processed.",
        ],
        "Statements & Access": [
            "Unable to download capital gain statement. Always fails.",
        ],
        "App Performance": [
            "App is very slow after update, takes 30 seconds to open holdings.",
            "Internal server error while opening portfolio. Worst experience.",
        ],
    }
    counts = {
        "NAV & Portfolio Display": 16, "Login & Authentication": 12,
        "Payments & Transactions": 6, "Statements & Access": 4, "App Performance": 2,
    }
    rows = []
    for theme, n in counts.items():
        pool = pools[theme]
        for i in range(n):
            d = start + timedelta(days=random.randint(0, span))
            rows.append({
                "date": d.isoformat(), "rating": random.choice([1, 1, 2, 2, 3]),
                "title": theme.split(" & ")[0] + " issue",
                "text": pool[i % len(pool)], "source": "Play Store",
            })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


def build_theme_distribution(df: pd.DataFrame) -> pd.DataFrame:
    dist = df["theme"].value_counts(normalize=True).mul(100).round(1)
    dist = dist.reindex(THEME_ORDER).fillna(0.0)
    return dist.reset_index().rename(columns={"index": "theme", "theme": "pct"}) \
        if "index" in dist.reset_index().columns else dist.reset_index(name="pct")


def pick_quotes(df: pd.DataFrame, top_themes: list, n: int = 3) -> list:
    quotes = []
    for theme in top_themes:
        subset = df[df["theme"] == theme]
        if len(subset):
            quotes.append(subset.iloc[0]["text"])
        if len(quotes) >= n:
            break
    while len(quotes) < n and len(df):
        for t in df["text"].tolist():
            if t not in quotes:
                quotes.append(t)
            if len(quotes) >= n:
                break
    return quotes[:n]


def build_pulse_note_md(df: pd.DataFrame, dist: pd.Series, date_range: str) -> str:
    top3 = dist.sort_values(ascending=False).head(3)
    top_theme_names = list(top3.index)
    quotes = pick_quotes(df, top_theme_names, 3)

    actions = []
    actions.append(f"1. {THEME_DEFS[top_theme_names[0]]['action']}")
    intents = ", ".join(f'"{THEME_DEFS[t]["description"].split(",")[0]}?"' for t in top_theme_names)
    actions.append(
        f"2. Support P0: Update my LIP-4 RAG Bot ({LIP4_URL}) with intents covering "
        f"the top issues ({', '.join(top_theme_names)}) to provide instant workarounds "
        f"and deflect ~50% of support tickets until the permanent fix is shipped."
    )
    second_theme = top_theme_names[1] if len(top_theme_names) > 1 else top_theme_names[0]
    actions.append(f"3. {THEME_DEFS[second_theme]['action']}")

    health = "CRITICAL" if top3.iloc[0] >= 30 else ("WATCH" if top3.iloc[0] >= 15 else "STABLE")

    lines = [
        "# HDFC MFOnline Investors — Weekly App Review Pulse",
        "",
        f"**Date:** {date_range} | **Reviews Analyzed:** {len(df)} | **Health:** {health}",
        "",
        "## Top 3 Themes",
        "",
    ]
    for i, theme in enumerate(top_theme_names, start=1):
        lines.append(f"{i}. **{theme} — {top3[theme]:.0f}%** — {THEME_DEFS[theme]['description']}")
    lines += ["", "## Real User Voice (anonymized)", ""]
    for q in quotes:
        lines.append(f"- \"{q}\"")
    lines += ["", "## 3 Action Ideas", ""]
    lines += actions
    lines += [
        "",
        "---",
        "",
        "**LIP 5 → LIP 4 connection:** LIP 5 reviews represent **Problem Discovery**; "
        f"the LIP 4 RAG Bot ([{LIP4_URL}]({LIP4_URL})) represents the **Solution**.",
    ]
    return "\n".join(lines)


def markdown_pulse_to_pdf(df: pd.DataFrame, dist: pd.Series, date_range: str) -> bytes:
    top3 = dist.sort_values(ascending=False).head(3)
    top_theme_names = list(top3.index)
    quotes = pick_quotes(df, top_theme_names, 3)
    second_theme = top_theme_names[1] if len(top_theme_names) > 1 else top_theme_names[0]
    health = "CRITICAL" if top3.iloc[0] >= 30 else ("WATCH" if top3.iloc[0] >= 15 else "STABLE")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                             leftMargin=0.7 * inch, rightMargin=0.7 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleC", parent=styles["Title"], fontSize=16, spaceAfter=4)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=10,
                                 textColor=colors.HexColor("#444444"), spaceAfter=10)
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10,
                               spaceAfter=6, textColor=colors.HexColor("#1F4E78"))
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14)

    health_color = "#C0392B" if health == "CRITICAL" else ("#B9770E" if health == "WATCH" else "#1E8449")

    story = [
        Paragraph("HDFC MFOnline Investors — Weekly App Review Pulse", title_style),
        Paragraph(
            f"Date: {date_range} &nbsp;|&nbsp; Reviews Analyzed: {len(df)} &nbsp;|&nbsp; "
            f"<font color='{health_color}'><b>Health: {health}</b></font>", meta_style),
        HRFlowable(width="100%", color=colors.HexColor("#1F4E78"), thickness=1),
        Paragraph("Top 3 Themes", h2_style),
    ]

    theme_data = [["Theme", "%", "Description"]]
    for theme in top_theme_names:
        theme_data.append([theme, f"{top3[theme]:.0f}%", THEME_DEFS[theme]["description"]])
    t = Table(theme_data, colWidths=[1.7 * inch, 0.5 * inch, 3.8 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7FA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    story.append(Paragraph("Real User Voice (anonymized)", h2_style))
    for q in quotes:
        story.append(Paragraph(f"&bull; \u201c{q}\u201d", body_style))
        story.append(Spacer(1, 3))

    story.append(Paragraph("3 Action Ideas", h2_style))
    story.append(Paragraph(f"<b>1.</b> {THEME_DEFS[top_theme_names[0]]['action']}", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"<b>2.</b> Support P0: Update the LIP-4 RAG Bot ({LIP4_URL}) with intents covering "
        f"the top issues to give instant workarounds and deflect ~50% of tickets until the "
        f"permanent fix ships.", body_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>3.</b> {THEME_DEFS[second_theme]['action']}", body_style))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#CCCCCC"), thickness=0.5))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>LIP 5 \u2192 LIP 4 connection:</b> LIP 5 reviews represent <b>Problem Discovery</b>; "
        "the LIP 4 RAG Bot represents the <b>Solution</b>.", body_style))

    doc.build(story)
    return buf.getvalue()


def build_email_draft(df: pd.DataFrame, dist: pd.Series, date_range: str) -> str:
    top3 = dist.sort_values(ascending=False).head(3)
    top_theme_names = list(top3.index)
    quotes = pick_quotes(df, top_theme_names, 3)
    second_theme = top_theme_names[1] if len(top_theme_names) > 1 else top_theme_names[0]
    combined_top2 = top3.iloc[0] + (top3.iloc[1] if len(top3) > 1 else 0)
    health = "CRITICAL" if top3.iloc[0] >= 30 else ("WATCH" if top3.iloc[0] >= 15 else "STABLE")

    top2_names = " & ".join(t.split(" & ")[0] for t in top_theme_names[:2])
    subject = (f"Weekly Pulse: HDFC MFOnline Investors - {top2_names} Account for "
               f"{combined_top2:.0f}% Complaints [Action Needed]")

    lines = [
        f"Subject: {subject}",
        "",
        "To: Product Team, Support Team",
        "From: App Review Insights Analyser (LIP 5)",
        "",
        "Hi team,",
        "",
        "Here is this week's Play Store review pulse for HDFC MFOnline Investors.",
        "",
        f"HEALTH STATUS: {health}",
        f"Reviews analyzed: {len(df)} ({date_range}), Play Store only, PII removed.",
        "",
        "TOP 3 ISSUES",
    ]
    for i, theme in enumerate(top_theme_names, start=1):
        lines.append(f"{i}. {theme} - {top3[theme]:.0f}% - {THEME_DEFS[theme]['description']}")
    lines += [
        "",
        f"Together, {' and '.join(top_theme_names[:2])} account for {combined_top2:.0f}% "
        "of all complaints this week.",
        "",
        "WHAT USERS ARE SAYING (anonymized)",
    ]
    for q in quotes:
        lines.append(f'- "{q}"')
    lines += [
        "",
        "3 ACTIONS FOR NEXT WEEK",
        f"1. {THEME_DEFS[top_theme_names[0]]['action']}",
        f"2. Support P0: Update the LIP-4 RAG Bot ({LIP4_URL}) with intents covering the top "
        "issues to give instant workarounds and deflect roughly 50% of support tickets until "
        "the permanent fix ships.",
        f"3. {THEME_DEFS[second_theme]['action']}",
        "",
        f"LIP 5 -> LIP 4 connection: LIP 5 (this review analysis) identifies the problems; "
        f"LIP 4, the RAG Bot at {LIP4_URL}, delivers the solution by answering these exact "
        "user questions instantly.",
        "",
        "Please let me know if you'd like a walkthrough of the full theme breakdown.",
        "",
        "Thanks,",
        "App Review Insights Analyser",
    ]
    return "\n".join(lines)


def make_sample_reviews_excel() -> bytes:
    df = load_sample_data()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Reviews", index=False)
    return buf.getvalue()


# ----------------------------------------------------------------------------
# Streamlit UI
# ----------------------------------------------------------------------------
st.set_page_config(page_title="HDFC MFOnline — App Review Insights Analyser", layout="wide")

st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:center;
                padding:14px 18px; background:#1F4E78; border-radius:8px; margin-bottom:18px;">
        <div>
            <span style="color:white; font-size:22px; font-weight:700;">
                📱 HDFC MFOnline Investors — App Review Insights Analyser
            </span><br/>
            <span style="color:#CFE0F0; font-size:13px;">LIP 5 · Problem Discovery for LIP 4</span>
        </div>
        <a href="{LIP4_URL}" target="_blank"
           style="background:white; color:#1F4E78; padding:8px 14px; border-radius:6px;
                  text-decoration:none; font-weight:600; font-size:13px;">
            🔗 Open LIP-4 RAG Bot
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("1. Upload Reviews")
    uploaded = st.file_uploader(
        "Upload Play Store reviews CSV",
        type=["csv"],
        help="Required columns: date, rating, title, text, source. No PII — usernames/emails/IDs.",
    )
    st.caption("No file yet? The app is preloaded with a 40-review sample so you can explore it.")
    st.divider()
    st.header("2. Sample Data")
    st.download_button(
        "⬇️ Download sample reviews (Excel)",
        data=make_sample_reviews_excel(),
        file_name="hdfc_mfonline_reviews.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

# --- Load & validate data ---
if uploaded is not None:
    try:
        raw_df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read the uploaded file: {e}")
        st.stop()
    missing = [c for c in REQUIRED_COLUMNS if c not in raw_df.columns]
    if missing:
        st.error(f"Uploaded CSV is missing required columns: {', '.join(missing)}")
        st.stop()
    source_label = "your uploaded file"
else:
    raw_df = load_sample_data()
    source_label = "the built-in 40-review sample (upload your own CSV in the sidebar to replace it)"

df = raw_df.copy()
for col in ["title", "text"]:
    df[col] = df[col].apply(scrub_pii)
df["theme"] = (df["title"].fillna("") + " " + df["text"].fillna("")).apply(classify_theme)

try:
    date_min = pd.to_datetime(df["date"]).min().strftime("%b %d, %Y")
    date_max = pd.to_datetime(df["date"]).max().strftime("%b %d, %Y")
    date_range = f"{date_min} - {date_max}"
except Exception:
    date_range = "Jun 28 - Sep 19, 2026"

st.info(f"Showing analysis for {source_label}. {len(df)} reviews · PII scrubbed automatically.")

# --- Theme distribution ---
st.subheader("Theme Distribution")
dist = df["theme"].value_counts(normalize=True).mul(100).round(1).reindex(THEME_ORDER).fillna(0.0)
col_chart, col_table = st.columns([2, 1])
with col_chart:
    st.bar_chart(dist)
with col_table:
    st.dataframe(
        pd.DataFrame({"Theme": dist.index, "% of Reviews": dist.values}),
        hide_index=True, use_container_width=True,
    )

with st.expander("View classified reviews"):
    st.dataframe(df[["date", "rating", "title", "text", "source", "theme"]],
                 hide_index=True, use_container_width=True)

st.divider()

# --- Weekly Pulse Note ---
st.subheader("📋 Weekly One-Page Pulse Note")
pulse_md = build_pulse_note_md(df, dist, date_range)
st.markdown(pulse_md)

pulse_pdf_bytes = markdown_pulse_to_pdf(df, dist, date_range)
c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "⬇️ Download Pulse Note (PDF)", data=pulse_pdf_bytes,
        file_name="weekly_pulse.pdf", mime="application/pdf", use_container_width=True,
    )
with c2:
    st.download_button(
        "⬇️ Download Pulse Note (Markdown)", data=pulse_md.encode("utf-8"),
        file_name="weekly_pulse.md", mime="text/markdown", use_container_width=True,
    )

st.divider()

# --- Email Draft ---
st.subheader("✉️ Email Draft")
email_text = build_email_draft(df, dist, date_range)
st.markdown("**Screenshot-ready view:**")
st.code(email_text, language=None)
st.download_button(
    "⬇️ Download Email Draft (TXT)", data=email_text.encode("utf-8"),
    file_name="email_draft.txt", mime="text/plain", use_container_width=True,
)

st.divider()

# --- README section ---
with st.expander("📖 README — How this app works"):
    st.markdown(f"""
**How to re-run for a new week**
1. Export the latest Play Store reviews (last 8–12 weeks) with columns:
   `date, rating, title, text, source`.
2. Remove usernames, emails, and IDs before uploading (the app also auto-scrubs common patterns).
3. Upload the CSV in the sidebar — the chart, pulse note, and email draft regenerate automatically.
4. Download the PDF/MD/TXT outputs and send the email draft to Product & Support.
5. Feed any new recurring issues into the LIP-4 bot's intents.

**Theme Legend (fixed set of 5 — never exceeded)**

| Theme | Covers |
|---|---|
| NAV & Portfolio Display | {THEME_DEFS['NAV & Portfolio Display']['description']} |
| Login & Authentication | {THEME_DEFS['Login & Authentication']['description']} |
| Payments & Transactions | {THEME_DEFS['Payments & Transactions']['description']} |
| Statements & Access | {THEME_DEFS['Statements & Access']['description']} |
| App Performance | {THEME_DEFS['App Performance']['description']} |

**Link to LIP 4:** [{LIP4_URL}]({LIP4_URL}) — LIP 5 identifies problems from reviews;
LIP 4 (the RAG bot) delivers the solution to users and support agents.
""")

st.caption(f"Generated {datetime.now().strftime('%b %d, %Y %H:%M')} · No PII stored or displayed.")
