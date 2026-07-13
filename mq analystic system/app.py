import streamlit as st
import pandas as pd
import base64
import numpy as np

from core.pipeline import run_pipeline

# =========================
# ✅ PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Data Analyst",
    layout="wide"
)

# =========================
# ✅ CUSTOM CSS (Modern UI)
# =========================
st.markdown("""
<style>

/* ✅ GLOBAL BACKGROUND (optional keep dark or change) */
body {
    background-color: #0f172a;
    color: white;
}

/* ✅ TEXT AREA (QUERY INPUT BOX) */
textarea {
    background-color: #fff9c4 !important;   /* light yellow */
    color: #000000 !important;             /* black text */
    border-radius: 10px !important;
}

/* ✅ INSIGHTS BOX */
.insight-box {
    background-color: #fff9c4;
    color: #000;
    padding: 15px;
    border-radius: 12px;
    margin-top: 10px;
}

/* ✅ SUMMARY BOX */
.summary-box {
    background-color: #fef08a;
    color: #000;
    padding: 15px;
    border-radius: 12px;
    margin-top: 10px;
}

/* ✅ INPUT LABEL */
label {
    color: #facc15 !important;
}

</style>
""", unsafe_allow_html=True)


# =========================
# ✅ HEADER
# =========================
st.markdown('<div class="title">🚀 AI Data Analyst Dashboard</div>', unsafe_allow_html=True)

# =========================
# ✅ FILE UPLOAD
# =========================
file = st.file_uploader("📂 Upload your dataset", type=["csv"])

query = st.text_area("💬 Ask your question about data")

# =========================
# ✅ LOAD DATA
# =========================
if file:
    df = pd.read_csv(file, low_memory=False)

    df.rename(columns={'FPCR\xa0No.': 'FPCR No.'}, inplace=True)
    fields = [
    "SBPR No.",
    "FTIR No.",
    "Product Model Code",
    "Sales Model Code",
    "Segmentation",
    "Subject (English)",
    "Causal Parts No.",
    "Rank",
    "Reported Country",
    "VIN",
    "Report Company",
    "Issued Company",
    "FTIR Report Date",
    "Reply Date",
    "Status",
    "FC-OK",
    "Date Registered",
    "Date of Incident",
    "Mileage / Using Time",
    "Days Used",
    "FPCR No.",
    "Engine No.",
    "Transmission No.",
    "Outbreak Country",
    "Sales Dealer",
    "Service Dealer",
    "Spec on Destination",
    "Causal Parts Name (English)",
    "Collection Request Date",
    "Parts Retrieved Date",
    "Manufacturer Factory",
    "Person of Action Judgement",
    "Department of Action Judgement",
    "Judgement Date",
    "Action Judgement",
    "Reason of \"Not to File as an SBPR\"",
    "Approval Judgement Date"
]


    df.columns=df.columns.str.strip()
    df=df[fields]
    # df.rename(columns={'FPCR\xa0No.': 'FPCR No.'}, inplace=True)
    def mlg_clean(s: str):
        try:
            return float(str(s).replace(",", "").split()[0])
        except Exception:
            return np.nan

    df['Mileage / Using Time'] = df['Mileage / Using Time'].apply(mlg_clean)
    df['Days Used'] = (
    df['Days Used']
    .astype(str)
    .str.extract(r'(\d+)', expand=False)
    )

    df['Days Used'] = pd.to_numeric(df['Days Used'], errors='coerce')

    df['Product Model Code']= df['Product Model Code'].str.slice(0, 3).copy()

    date_columns=['FTIR Report Date', 'Reply Date', 'Date of Incident', 'Judgement Date','Approval Judgement Date']
    # df[date_columns]=df[date_columns].apply(pd.to_datetime)
    df[date_columns] = df[date_columns].apply(
    pd.to_datetime,
    format='mixed',
    errors='coerce'
                        )

    st.markdown("### 🔍 Dataset Preview")
    st.dataframe(df.head())

    # =========================
    # ✅ RUN BUTTON
    # =========================
    if st.button("Run Analysis 🚀"):

        with st.spinner("Thinking... 🤖"):
            output = run_pipeline(query, df)

        # =========================
        # ✅ ERROR HANDLING
        # =========================
        if "error" in output:
            st.error(output["error"])

        else:
            col1, col2 = st.columns(2)

            # =========================
            # ✅ RESULT
            # =========================
            with col1:
                st.markdown("### 📌 Result")
                st.write(output["result"])

            # =========================
            # ✅ VISUALIZATION
            # =========================
            with col2:
                st.markdown("### 📊 Visualizations")
                if output["images"]:
                    for img in output["images"]:
                        st.image(base64.b64decode(img))
                else:
                    st.info("No plots generated")

            # =========================
            # ✅ CODE
            # =========================
            st.markdown("### 🧾 Generated Code / SQL")
            st.code(output["code"], language="python")

            # =========================
            # ✅ INSIGHTS
            # =========================
            # st.markdown("### 🧠 Insights")
            # st.markdown(f'<div class="card">{output["insights"]}</div>', unsafe_allow_html=True)

            st.markdown(
                f"<div class='insight-box'>{output['insights']}</div>",
                unsafe_allow_html=True
)

            # =========================
            # ✅ BUSINESS SUMMARY
            # =========================
            st.markdown("### 💼 Business Summary")
            # st.success(output["summary"])

            st.markdown(
            f"<div class='summary-box'>{output['summary']}</div>",
            unsafe_allow_html=True
        )
