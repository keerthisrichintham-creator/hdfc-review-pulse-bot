# HDFC MFOnline Investors — App Review Insights Analyser (LIP 5)

A Streamlit app that turns Play Store reviews of **HDFC MFOnline Investors** into a
weekly, scannable "pulse note" and an action-ready email draft for the Product and
Support teams — and connects those findings to the **LIP 4 RAG Chatbot**
([hdfc-bot.streamlit.app](https://hdfc-bot.streamlit.app)), which delivers the fix.

LIP 5 = **Problem Discovery** (this app). LIP 4 = **Solution** (the RAG bot).

## How to re-run this for a new week

1. Export the latest Play Store reviews for HDFC MFOnline Investors (last 8–12 weeks
   recommended) into a CSV with columns: `date, rating, title, text, source`.
2. Strip any usernames, emails, or reviewer IDs before uploading — the app assumes
   the file is already PII-free.
3. Open the app and upload the CSV using the file uploader in the sidebar.
4. The app automatically buckets every review into one of the 5 fixed themes below,
   computes the % distribution, and regenerates:
   - the bar chart,
   - the one-page Weekly Pulse Note (Markdown + PDF download),
   - the email draft (TXT download).
5. Download whatever you need and send the email draft to Product/Support.
6. Update the LIP-4 bot's intents with any new recurring issues you see.

## Theme Legend (max 5 — fixed, do not exceed)

| Theme | Covers |
|---|---|
| **NAV & Portfolio Display** | NAV date/value missing, portfolio amount rounded instead of exact, XIRR per scheme missing, units not visible after update |
| **Login & Authentication** | OTP not received, account blocked after 3 attempts, logout → network error loop, session expired, auto-logout |
| **Payments & Transactions** | SIP payment deducted but not reflecting, redemption stuck 3+ days, payment failed |
| **Statements & Access** | Unable to download capital gain statement, statement password not working, monthly statement fails |
| **App Performance** | App is slow, takes 30+ seconds to open, internal server error, crash |

A review is matched to a theme by keyword rules built from the definitions above;
you can override any review's theme manually in the app if the keyword match is wrong.

## Link to LIP 4

Every pulse note and email draft references the LIP-4 RAG Chatbot, which should be
kept up to date with instant-answer intents for the top-recurring issues:
👉 https://hdfc-bot.streamlit.app

## Files in this package

- `app.py` — the Streamlit application
- `hdfc_mfonline_reviews.xlsx` — sample 40-review dataset (Play Store, PII-free) to test the app
- `weekly_pulse.pdf` / generated `weekly_pulse.md` — the one-page pulse note
- `email_draft.txt` — ready-to-send email to Product/Support
- `README.md` — this file

## Privacy

No usernames, emails, or reviewer IDs are collected or displayed anywhere in the
app, sample data, or generated outputs.
