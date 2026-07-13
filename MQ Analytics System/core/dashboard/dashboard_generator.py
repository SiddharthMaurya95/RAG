import streamlit as st
import pandas as pd
import base64

def render_dashboard(output):
    st.markdown("## 📊 AI Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📌 Result")
        st.write(output["result"])

    with col2:
        st.markdown("### 📈 Visualization")
        for img in output["images"]:
            st.image(base64.b64decode(img))

    st.markdown("### 🧠 Insights")
    st.info(output["insights"])

    st.markdown("### 💼 Business Summary")
    st.success(output["summary"])