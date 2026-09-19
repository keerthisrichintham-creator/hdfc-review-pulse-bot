# HDFC MFOnline Investors — Weekly App Review Pulse

**Date:** Jun 28 – Sep 19, 2026 | **Reviews Analyzed:** 40 | **Health:** 🔴 CRITICAL

## Top 3 Themes

1. **NAV & Portfolio Display — 40%** — NAV date/value missing, portfolio rounded instead of exact, XIRR per scheme gone.
2. **Login & Authentication — 30%** — OTP delays, accounts blocked after 3 attempts, logout loops.
3. **Payments & Transactions — 15%** — SIP deductions not reflecting, redemptions stuck 3+ days.

## Real User Voice (anonymized)

- "NAV not showing anywhere after new update. Cannot see today's NAV or units."
- "Every time I logout it says network error. OTP not received. Login loop."
- "SIP payment deducted but not showing in app. Very frustrating."

## 3 Action Ideas

1. **Product (P0):** Restore NAV Dashboard — show NAV date, NAV value, exact amount, units, and XIRR per scheme.
2. **Support (P0):** Update the LIP-4 RAG Bot ([hdfc-bot.streamlit.app](https://hdfc-bot.streamlit.app)) with 3 intents — "Where is NAV?", "Login failure?", "SIP deducted but not showing?" — to give instant workarounds and deflect ~50% of tickets until the permanent fix ships.
3. **Engineering (P1):** Fix the session-persistence bug causing logout → network-error loops. Add retry logic, a clear error message, and auto-unblock after 30 minutes.

---

**LIP 5 → LIP 4 connection:** LIP 5 (this review analysis) represents **Problem Discovery**; LIP 4 (the RAG Bot) represents the **Solution** — surfacing instant, accurate answers to the exact issues users are reporting here.
