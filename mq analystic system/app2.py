# import streamlit as st
# import pandas as pd
# import base64
# import numpy as np

# from core.pipeline import run_pipeline

# # =========================
# # ✅ PAGE CONFIG
# # =========================
# st.set_page_config(
#     page_title="AI Data Analyst",
#     layout="wide"
# )

# # =========================
# # ✅ CUSTOM CSS
# # =========================
# st.markdown("""
# <style>

# /* ✅ GLOBAL BACKGROUND */
# body {
#     background: linear-gradient(to right, #0f172a, #1e293b);
#     color: white;
#     font-family: 'Segoe UI', sans-serif;
# }

# /* ✅ HEADER */
# .title {
#     font-size: 42px;
#     font-weight: 700;
#     text-align: center;
# }

# .subtitle {
#     text-align: center;
#     font-size: 16px;
#     color: #cbd5f5;
#     margin-bottom: 25px;
# }

# /* ✅ INPUT BOX */
# textarea {
#     background-color: #fff9c4 !important;
#     color: #000 !important;
#     border-radius: 10px !important;
# }

# /* ✅ CARDS */
# .card {
#     padding: 15px;
#     border-radius: 12px;
#     background-color: #1e293b;
#     box-shadow: 0 4px 15px rgba(0,0,0,0.3);
#     margin-bottom: 15px;
# }

# /* ✅ INSIGHTS */
# .insight-box {
#     background-color: #fff9c4;
#     color: #000;
#     padding: 15px;
#     border-radius: 12px;
# }

# /* ✅ SUMMARY */
# .summary-box {
#     background-color: #fef08a;
#     color: #000;
#     padding: 15px;
#     border-radius: 12px;
# }

# /* ✅ DISCLAIMER */
# .disclaimer {
#     background-color: #7f1d1d;
#     color: #fecaca;
#     padding: 12px;
#     border-radius: 10px;
#     font-size: 13px;
#     margin-top: 20px;
# }

# /* ✅ LABEL */
# label {
#     color: #facc15 !important;
# }

# /* ✅ BUTTON */
# button {
#     border-radius: 10px !important;
# }

# </style>
# """, unsafe_allow_html=True)

# # =========================
# # ✅ HEADER
# # =========================
# st.markdown('<div class="title">🚀 AI Data Analyst</div>', unsafe_allow_html=True)
# st.markdown('<div class="subtitle">Turn raw data into insights, visualizations & business decisions instantly</div>', unsafe_allow_html=True)

# # =========================
# # ✅ INPUT CARD
# # =========================
# st.markdown('<div class="card">', unsafe_allow_html=True)
# file = st.file_uploader("📂 Upload your dataset", type=["csv"])
# query = st.text_area("💬 Ask your question about data")
# st.markdown('</div>', unsafe_allow_html=True)

# # =========================
# # ✅ LOAD & CLEAN DATA
# # =========================
# if file:
#     df = pd.read_csv(file, low_memory=False)

#     df.rename(columns={'FPCR\xa0No.': 'FPCR No.'}, inplace=True)

#     fields = [
#         "SBPR No.", "FTIR No.", "Product Model Code", "Sales Model Code",
#         "Segmentation", "Subject (English)", "Causal Parts No.", "Rank",
#         "Reported Country", "VIN", "Report Company", "Issued Company",
#         "FTIR Report Date", "Reply Date", "Status", "FC-OK",
#         "Date Registered", "Date of Incident", "Mileage / Using Time",
#         "Days Used", "FPCR No.", "Engine No.", "Transmission No.",
#         "Outbreak Country", "Sales Dealer", "Service Dealer",
#         "Spec on Destination", "Causal Parts Name (English)",
#         "Collection Request Date", "Parts Retrieved Date",
#         "Manufacturer Factory", "Person of Action Judgement",
#         "Department of Action Judgement", "Judgement Date",
#         "Action Judgement", "Reason of \"Not to File as an SBPR\"",
#         "Approval Judgement Date"
#     ]

#     df.columns = df.columns.str.strip()
#     df = df[fields]

#     # ✅ CLEAN FUNCTIONS
#     def mlg_clean(s):
#         try:
#             return float(str(s).replace(",", "").split()[0])
#         except:
#             return np.nan

#     df['Mileage / Using Time'] = df['Mileage / Using Time'].apply(mlg_clean)

#     df['Days Used'] = (
#         df['Days Used']
#         .astype(str)
#         .str.extract(r'(\d+)', expand=False)
#     )
#     df['Days Used'] = pd.to_numeric(df['Days Used'], errors='coerce')

#     df['Product Model Code'] = df['Product Model Code'].str.slice(0, 3)

#     date_columns = [
#         'FTIR Report Date', 'Reply Date',
#         'Date of Incident', 'Judgement Date', 'Approval Judgement Date'
#     ]

#     df[date_columns] = df[date_columns].apply(
#         pd.to_datetime, format='mixed', errors='coerce'
#     )

#     # =========================
#     # ✅ PREVIEW
#     # =========================
#     st.markdown("### 🔍 Dataset Preview")
#     st.dataframe(df.head())

#     # =========================
#     # ✅ RUN BUTTON
#     # =========================
#     if st.button("Run Analysis 🚀"):

#         with st.spinner("Thinking... 🤖"):
#             output = run_pipeline(query, df)

#         # =========================
#         # ✅ ERROR HANDLING
#         # =========================
#         if "error" in output:
#             st.error(output["error"])

#         else:
#             col1, col2 = st.columns(2)

#             # ✅ RESULT
#             with col1:
#                 st.markdown('<div class="card">', unsafe_allow_html=True)
#                 st.markdown("### 📌 Result")
#                 st.write(output["result"])
#                 st.markdown('</div>', unsafe_allow_html=True)

#             # ✅ VISUALIZATION
#             with col2:
#                 st.markdown('<div class="card">', unsafe_allow_html=True)
#                 st.markdown("### 📊 Visualizations")
#                 if output["images"]:
#                     for img in output["images"]:
#                         st.image(base64.b64decode(img))
#                 else:
#                     st.info("No plots generated")
#                 st.markdown('</div>', unsafe_allow_html=True)

#             # ✅ CODE
#             st.markdown('<div class="card">', unsafe_allow_html=True)
#             st.markdown("### 🧾 Generated Code / SQL")
#             st.code(output["code"], language="python")
#             st.markdown('</div>', unsafe_allow_html=True)

#             # ✅ INSIGHTS
#             st.markdown("### 🧠 Insights")
#             st.markdown(
#                 f"<div class='insight-box'>{output['insights']}</div>",
#                 unsafe_allow_html=True
#             )

#             # ✅ SUMMARY
#             st.markdown("### 💼 Business Summary")
#             st.markdown(
#                 f"<div class='summary-box'>{output['summary']}</div>",
#                 unsafe_allow_html=True
#             )

# # =========================
# # ✅ DISCLAIMER
# # =========================
# st.markdown("""
# <div class='disclaimer'>
# ⚠️ <b>Disclaimer:</b> AI-generated results may contain inaccuracies.
# Please validate outputs before using them for business-critical decisions.
# </div>
# """, unsafe_allow_html=True)


import streamlit as st
import pandas as pd
import base64
import numpy as np
import matplotlib.pyplot as plt  # ✅ IMPORTANT

from core.pipeline import run_pipeline

# =========================
# ✅ PAGE CONFIG
# =========================
st.set_page_config(
    page_title="AI Data Analyst",
    layout="wide"
)

# =========================
# ✅ CUSTOM CSS
# =========================
st.markdown("""
<style>
body {
    background: linear-gradient(to right, #0f172a, #1e293b);
    color: white;
    font-family: 'Segoe UI', sans-serif;
}
.title {
    font-size: 42px;
    font-weight: 700;
    text-align: center;
}
.subtitle {
    text-align: center;
    font-size: 16px;
    color: #cbd5f5;
    margin-bottom: 25px;
}
textarea {
    background-color: #fff9c4 !important;
    color: #000 !important;
    border-radius: 10px !important;
}
.card {
    padding: 15px;
    border-radius: 12px;
    background-color: #1e293b;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    margin-bottom: 15px;
}
.insight-box {
    background-color: #fff9c4;
    color: #000;
    padding: 15px;
    border-radius: 12px;
}
.summary-box {
    background-color: #fef08a;
    color: #000;
    padding: 15px;
    border-radius: 12px;
}
.disclaimer {
    background-color: #7f1d1d;
    color: #fecaca;
    padding: 12px;
    border-radius: 10px;
    font-size: 13px;
    margin-top: 20px;
}
label {
    color: #facc15 !important;
}
button {
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================
# ✅ HEADER
# =========================
st.markdown('<div class="title">🚀 AI Data Analyst</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Turn raw data into insights, visualizations & business decisions instantly</div>', unsafe_allow_html=True)

# =========================
# ✅ INPUT CARD
# =========================
st.markdown('<div class="card">', unsafe_allow_html=True)
file = st.file_uploader("📂 Upload your dataset", type=["csv"])
query = st.text_area("💬 Ask your question about data")
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# ✅ LOAD & CLEAN DATA
# =========================
if file:
    df = pd.read_csv(file, low_memory=False)

    df.rename(columns={'FPCR\xa0No.': 'FPCR No.'}, inplace=True)

    fields = [
        "SBPR No.", "FTIR No.", "Product Model Code", "Sales Model Code",
        "Segmentation", "Subject (English)", "Causal Parts No.", "Rank",
        "Reported Country", "VIN", "Report Company", "Issued Company",
        "FTIR Report Date", "Reply Date", "Status", "FC-OK",
        "Date Registered", "Date of Incident", "Mileage / Using Time",
        "Days Used", "FPCR No.", "Engine No.", "Transmission No.",
        "Outbreak Country", "Sales Dealer", "Service Dealer",
        "Spec on Destination", "Causal Parts Name (English)",
        "Collection Request Date", "Parts Retrieved Date",
        "Manufacturer Factory", "Person of Action Judgement",
        "Department of Action Judgement", "Judgement Date",
        "Action Judgement", "Reason of \"Not to File as an SBPR\"",
        "Approval Judgement Date"
    ]

    df.columns = df.columns.str.strip()
    df = df[fields]

    def mlg_clean(s):
        try:
            return float(str(s).replace(",", "").split()[0])
        except:
            return np.nan

    df['Mileage / Using Time'] = df['Mileage / Using Time'].apply(mlg_clean)

    df['Days Used'] = df['Days Used'].astype(str).str.extract(r'(\d+)', expand=False)
    df['Days Used'] = pd.to_numeric(df['Days Used'], errors='coerce')

    df['Product Model Code'] = df['Product Model Code'].str.slice(0, 3)

    date_columns = [
        'FTIR Report Date', 'Reply Date',
        'Date of Incident', 'Judgement Date', 'Approval Judgement Date'
    ]

    df[date_columns] = df[date_columns].apply(
        pd.to_datetime, format='mixed', errors='coerce'
    )

    # =========================
    # ✅ PREVIEW
    # =========================
    st.markdown("### 🔍 Dataset Preview")
    st.dataframe(df.head())

    # =========================
    # ✅ RUN BUTTON
    # =========================
    if st.button("Run Analysis 🚀"):

        with st.spinner("Thinking... 🤖"):
            output = run_pipeline(query, df)

        if "error" in output:
            st.error(output["error"])

        else:
            col1, col2 = st.columns(2)

            # =========================
            # ✅ RESULT
            # =========================
            with col1:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### 📌 Result")
                st.write(output.get("result"))
                st.markdown('</div>', unsafe_allow_html=True)

            # =========================
            # ✅ VISUALIZATION (FIXED 🔥)
            # =========================
            with col2:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.markdown("### 📊 Visualizations")

                # ✅ 1. Images from executor
                if output.get("images"):
                    for img in output["images"]:
                        st.image(base64.b64decode(img))

                # ✅ 2. Auto visualization agent
                elif output.get("visualization"):
                    st.success(output["visualization"])

                    # ✅ ensure matplotlib renders
                    st.pyplot(plt)

                else:
                    st.info("No visualization available")

                st.markdown('</div>', unsafe_allow_html=True)

            # =========================
            # ✅ CODE
            # =========================
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 🧾 Generated Code / SQL")
            st.code(output.get("code"), language="python")
            st.markdown('</div>', unsafe_allow_html=True)

            # =========================
            # ✅ INTENT (NEW 🔥)
            # =========================
            if output.get("intent"):
                st.markdown("### 🧠 Detected Intent")
                st.write(output["intent"])

            # =========================
            # ✅ INSIGHTS
            # =========================
            st.markdown("### 🧠 Insights")
            st.markdown(
                f"<div class='insight-box'>{output.get('insights')}</div>",
                unsafe_allow_html=True
            )

            # =========================
            # ✅ SUMMARY
            # =========================
            st.markdown("### 💼 Business Summary")
            st.markdown(
                f"<div class='summary-box'>{output.get('summary')}</div>",
                unsafe_allow_html=True
            )

# =========================
# ✅ DISCLAIMER
# =========================
st.markdown("""
<div class='disclaimer'>
⚠️ <b>Disclaimer:</b> AI-generated results may contain inaccuracies.
Please validate outputs before using them for business-critical decisions.
</div>
""", unsafe_allow_html=True)