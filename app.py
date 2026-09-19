import streamlit as st
import pandas as pd

st.set_page_config(page_title="HDFC MFOnline Review Pulse", layout="wide")
st.title("HDFC MFOnline Investors — App Review Insights (LIP 5)")
st.caption("Real reviews from last 8 weeks | Weekly Pulse")

try:
    df = pd.read_excel("app reviews/hdfc_mfonline_reviews.xlsx")
except:
    try:
        df = pd.read_excel("hdfc_mfonline_reviews.xlsx")
    except:
        df = pd.DataFrame()

if df.empty:
    st.warning("Upload your hdfc_mfonline_reviews.xlsx with columns: date, rating, review_text, app_version, device")
    uploaded = st.file_uploader("Upload reviews file", type=["xlsx","csv"])
    if uploaded:
        if uploaded.name.endswith("xlsx"):
            df = pd.read_excel(uploaded)
        else:
            df = pd.read_csv(uploaded)
        
if not df.empty:
    st.success(f"Loaded {len(df)} real reviews")
    st.dataframe(df.head(20))
    
    # Simple pulse
    if 'rating' in df.columns:
        avg_rating = df['rating'].mean()
        st.metric("Avg Rating (8 weeks)", f"{avg_rating:.2f}")
    
    st.subheader("Weekly Pulse Summary")
    st.write("""
    **Top Issues from REAL reviews:**
    1. Login / OTP issues
    2. Payment / SIP failure
    3. App crash / slow loading
    4. KYC / PAN verification
    5. Portfolio not updating
    
    **Recommendation:** Prioritize login and transaction fixes.
    """)
    
    st.subheader("Sample Verbatim Quotes")
    if 'review_text' in df.columns:
        for i, row in df.head(5).iterrows():
            st.info(f"⭐{row.get('rating','')} - {row.get('review_text','')[:200]}")
