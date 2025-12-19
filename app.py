import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Texas Diabetes Risk Chatbot",
    page_icon="🩺",
    layout="wide"
)

# Small CSS polish (safe + subtle)
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stMetric { padding: 0.25rem 0.25rem; }
    </style>
    """,
    unsafe_allow_html=True
)


# Load your dataset (merged_all)
data = pd.read_csv("fulldata_with_risk.csv") # <-- replace this with your dataset filename

data["County"] = data["County"].astype(str).str.strip()

# Build county list (exclude Texas from dropdown)
counties = sorted(
    [c for c in data["County"].dropna().unique() if c.lower() != "texas"]
)
# Add Risk Category labels (Low / Moderate / High)
# ----------------------------
# If Risk_Percentile exists, use it. Otherwise create it from Risk_Score.
if "Risk_Percentile" not in data.columns and "Risk_Score" in data.columns:
    # Percentile from score, higher score = higher risk
    tmp = data.copy()
    tmp_counties = tmp[tmp["County"].str.lower() != "texas"].copy()
    tmp_counties["Risk_Percentile"] = tmp_counties["Risk_Score"].rank(pct=True) * 100
    data = data.merge(
        tmp_counties[["County", "Risk_Percentile"]],
        on="County",
        how="left"
    )

if "Risk_Category" not in data.columns and "Risk_Percentile" in data.columns:
    data["Risk_Category"] = pd.cut(
        data["Risk_Percentile"],
        bins=[0, 33.33, 66.66, 100],
        labels=["Low", "Moderate", "High"],
        include_lowest=True
    )

# Texas reference value for diabetes (if present)
texas_diabetes = None
texas_row = data[data["County"].str.lower() == "texas"]
if not texas_row.empty and "Diabetes" in data.columns:
    texas_diabetes = texas_row["Diabetes"].iloc[0]

# Helpers
# ----------------------------
def find_county_from_text(user_text: str) -> str | None:
    """Try to find a county name mentioned in the user text."""
    msg = (user_text or "").lower()
    for c in counties:
        if c.lower() in msg:
            return c
    return None

def county_snapshot(county: str) -> dict:
    row = data.loc[data["County"] == county].iloc[0].to_dict()
    return row

def risk_explanation(row: dict) -> str:
    """Short, user-friendly explanation paragraph."""
    parts = []

    # Benchmark vs Texas average diabetes
    if texas_diabetes is not None and "Diabetes" in row and pd.notna(row["Diabetes"]):
        if row["Diabetes"] > texas_diabetes:
            parts.append(f"This county’s diabetes prevalence is **above** the Texas overall value (**{texas_diabetes:.1f}%**).")
        else:
            parts.append(f"This county’s diabetes prevalence is **below** the Texas overall value (**{texas_diabetes:.1f}%**).")

# Composite risk label
    if "Risk_Category" in row and pd.notna(row["Risk_Category"]):
        parts.append(f"Overall, the composite risk level is **{row['Risk_Category']}**.")

    # Why the risk might be high (simple heuristics)
    drivers = []
    if "Obesity" in row and pd.notna(row["Obesity"]) and row["Obesity"] >= 35:
        drivers.append("higher obesity")
    if "Uninsured" in row and pd.notna(row["Uninsured"]) and row["Uninsured"] >= 15:
        drivers.append("higher uninsured rate")
    if "Median_Income" in row and pd.notna(row["Median_Income"]) and row["Median_Income"] <= 60000:
        drivers.append("lower median income")

    if drivers:
        parts.append("Key drivers in this profile include " + ", ".join(drivers) + ".")

# PM2.5 note (based on your earlier correlations, it was weak)
    if "PM2.5" in row and pd.notna(row["PM2.5"]):
        parts.append("PM2.5 is included for context; in this dataset it showed a weaker direct county-level correlation with diabetes than obesity, income, and uninsured rate.")

    return " ".join(parts) if parts else "Ask about another county or explore the Rankings tab."


# --- Your chatbot function ---
def chatbot(message):
    msg = message.lower()
    
    for county in data['County']:
        if county.lower() in msg:
            row = data[data['County'] == county].iloc[0]

            response = f"""
Here are the health stats for {county}:

• Diabetes rate: {row['Diabetes']}%
• Obesity rate: {row['Obesity']}%
• Uninsured: {row['Uninsured']}%
• Median Income: ${row['Median_Income']:,.0f}
• Composite Risk Score: {row['Risk_Score']:.2f}
• Risk Rank (TX counties): {int(row['Risk_Rank'])}
"""
            return response

    return "I couldn't find that county. Try asking about a Texas county!"

# Sidebar Navigation + Quick Lookup
# ----------------------------
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to:", ["Chat", "Rankings", "About"], index=0)

st.sidebar.divider()
st.sidebar.subheader("Quick County Lookup")
selected = st.sidebar.selectbox("Select a county:", ["(choose)"] + counties)

if selected != "(choose)":
    row = county_snapshot(selected)
    st.sidebar.markdown(f"**{selected}**")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        st.metric("Diabetes %", f"{row.get('Diabetes', 'N/A')}")
        st.metric("Uninsured %", f"{row.get('Uninsured', 'N/A')}")
    with c2:
        st.metric("Obesity %", f"{row.get('Obesity', 'N/A')}")
        st.metric("Risk Rank", f"{int(row.get('Risk_Rank')) if pd.notna(row.get('Risk_Rank', None)) else 'N/A'}")
# Main Pages
# ----------------------------
st.title("🩺 Texas Diabetes Risk Chatbot")

if page == "About":
    st.subheader("About this app")
    st.write(
        """
**Purpose**
This application is designed for **educational, research, and exploratory purposes**.
It summarizes population-level health indicators and should **not** be used for individual medical diagnosis or treatment decisions.

This app summarizes county-level diabetes-related indicators for Texas and provides a **composite risk score**
based on multiple factors (obesity, uninsured rate, and median income). It is designed for learning, exploration,
and public health analytics—not individual medical diagnosis.

**Data sources**
- Texas County Health Rankings & Roadmaps (CHR&R)
- Publicly available county-level indicators for Texas


**Beta notice**
This website is currently in **continuous beta**. Features, data sources, and risk models are actively being improved and expanded over time.

**Interpretation note**
All analyses are observational and descriptive. Associations shown do **not** imply causation.
"""
    )
    if texas_diabetes is not None:
        st.info(f"Texas reference diabetes prevalence in this dataset: **{texas_diabetes:.1f}%**")
    st.stop()

if page == "Rankings":
    st.subheader("📊 Composite Risk Rankings (Texas Counties)")

    df_counties = data[data["County"].str.lower() != "texas"].copy()

    k = st.slider("Show top N counties:", 5, 50, 10)

    left, right = st.columns(2)

    with left:
        st.markdown(f"### 🔥 Top {k} Highest Risk")
        st.dataframe(
            df_counties.sort_values("Risk_Score", ascending=False)
            .head(k)[["County", "Risk_Category", "Risk_Score", "Risk_Rank", "Diabetes", "Obesity", "Uninsured", "Median_Income"]],
            use_container_width=True
        )

    with right:
        st.markdown(f"### 🌿 Top {k} Lowest Risk")
        st.dataframe(
            df_counties.sort_values("Risk_Score", ascending=True)
            .head(k)[["County", "Risk_Category", "Risk_Score", "Risk_Rank", "Diabetes", "Obesity", "Uninsured", "Median_Income"]],
            use_container_width=True
        )

    st.divider()
    st.caption("Rankings exclude the statewide 'Texas' row. Use Texas as a benchmark in the Chat tab.")
    st.stop()

# ----------------------------
# Chat Page (with chat bubbles + history)       
# --- Streamlit UI ---
# ----------------------------
# Chat Page (bubble chat + history)
# ----------------------------
if page == "Chat":
    st.subheader("💬 Chat")
    st.caption("Try: “Harris County” or “How risky is Travis County?”")

    # Create chat history if it doesn't exist yet
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Show past messages
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # Input box at the bottom
    user_input = st.chat_input("Type your question…")

    if user_input:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Find county in the message (or use sidebar dropdown if selected)
        county_found = find_county_from_text(user_input)
        if county_found is None and selected != "(choose)":
            county_found = selected

        # Respond
        if county_found is None:
            answer = "I couldn’t find a Texas county in your message. Try **“Harris County”** or pick one from the sidebar."
        else:
            row = county_snapshot(county_found)

            # Main stats (your existing chatbot response)
            answer = chatbot(county_found)

            # Add your short explanation paragraph too
            answer += "\n\n**Quick interpretation:** " + risk_explanation(row)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.markdown(answer)
