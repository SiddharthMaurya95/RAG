import os
import sys
import time
import datetime
import threading
import sqlite3
import streamlit as st
import pandas as pd

# Add the parent directory (automotive_qa root) to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import local modules
from auth.session import (
    verify_or_create_user, 
    get_user_chat_history, 
    add_chat_message,
    create_chat_session,
    get_user_chat_sessions,
    get_session_chat_history,
    update_chat_session_title,
    delete_chat_session
)
from core.singletons import get_db_connection, get_embedder, get_llm, get_ingestion_tracker
from core.router import QueryRouter
from core.paths import get_inbox_path, get_project_root
from etl.manual_ingest import scan_and_ingest_inbox
from viz.charts import (
    plot_horizontal_bar, 
    plot_line_trend, 
    plot_donut_chart, 
    plot_histogram, 
    plot_radar_comparison,
    plot_grouped_bar
)

# Set Page Config
st.set_page_config(
    page_title="Automotive QA Intelligence",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Inject Enterprise Styling
def inject_custom_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        /* ── Base ── */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #f8fafc;
            color: #334155;
        }
        
        /* Hide Streamlit Deploy Button */
        .stAppDeployButton {
            display: none !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
            font-weight: 600;
            color: #0f172a;
            letter-spacing: -0.01em;
        }

        /* ── Sidebar ── */
        [data-testid="stSidebar"] {
            background-color: #f1f5f9 !important;
            border-right: 1px solid #e2e8f0;
        }

        /* ── Buttons ── */
        .element-container button[kind="primary"] {
            background-color: #0ea5e9 !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 600;
            border-radius: 6px;
            padding: 0.45rem 1rem;
            transition: background-color 0.15s ease;
        }
        .element-container button[kind="primary"]:hover {
            background-color: #0284c7 !important;
        }
        .element-container button[kind="secondary"] {
            background-color: #ffffff !important;
            color: #475569 !important;
            border: 1px solid #e2e8f0 !important;
            font-weight: 500;
            border-radius: 6px;
            transition: border-color 0.15s ease, color 0.15s ease;
        }
        .element-container button[kind="secondary"]:hover {
            border-color: #94a3b8 !important;
            color: #0f172a !important;
        }

        /* Logout */
        .logout-btn-container button {
            background-color: #ffffff !important;
            color: #dc2626 !important;
            border: 1px solid #fecaca !important;
            font-weight: 500;
            border-radius: 6px;
            transition: background-color 0.15s ease;
        }
        .logout-btn-container button:hover {
            background-color: #fef2f2 !important;
        }

        /* ── Cards ── */
        .glass-card {
            background: #ffffff;
            border-radius: 8px;
            padding: 20px;
            border: 1px solid #e2e8f0;
            margin-bottom: 16px;
        }

        /* ── Metric cards — flat white + colored top border ── */
        .metric-card {
            background: #ffffff;
            border-radius: 8px;
            padding: 18px 20px;
            border: 1px solid #e2e8f0;
            margin-bottom: 16px;
        }
        .metric-card-blue   { border-top: 3px solid #3b82f6; }
        .metric-card-teal   { border-top: 3px solid #14b8a6; }
        .metric-card-amber  { border-top: 3px solid #f59e0b; }
        .metric-card-emerald { border-top: 3px solid #10b981; }

        .metric-value {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
            font-family: 'Inter', sans-serif;
            margin-top: 6px;
            letter-spacing: -0.02em;
        }
        .metric-label {
            font-size: 11px;
            color: #64748b;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        /* ── Section headers ── */
        .section-label {
            font-size: 11px;
            font-weight: 600;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 8px;
        }

        /* ── Welcome ── */
        .welcome-container {
            text-align: left;
            margin-top: 0.5rem;
            margin-bottom: 1.5rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid #e2e8f0;
        }
        .welcome-title {
            font-size: 1.75rem !important;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .welcome-subtitle {
            font-size: 0.95rem;
            color: #64748b;
            line-height: 1.5;
            max-width: 700px;
        }

        /* ── Intent badges ── */
        .intent-badge {
            display: inline-block;
            font-size: 10px;
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 4px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .badge-search     { background: #eff6ff; color: #1d4ed8; }
        .badge-analytics  { background: #f0fdfa; color: #0f766e; }
        .badge-visualize  { background: #ecfdf5; color: #047857; }
        .badge-compare    { background: #fffbeb; color: #b45309; }
        .badge-report     { background: #f1f5f9; color: #475569; }
        .badge-ambiguous  { background: #faf5ff; color: #7e22ce; }

        /* ── Citation cards ── */
        .citation-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-left: 3px solid #3b82f6;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }

        /* ── Chat messages ── */
        [data-testid="stChatMessage"] {
            border-radius: 8px !important;
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            margin-bottom: 12px !important;
            padding: 16px 20px !important;
            color: #334155 !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
            background-color: #f8fafc !important;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] li {
            color: #334155 !important;
        }

        /* ── Expander ── */
        [data-testid="stExpander"] {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }

        /* ── Dataframe ── */
        [data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 6px;
        }

        /* ── Chart container ── */
        .chart-container {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 8px 4px 8px;
            margin-bottom: 16px;
        }

        /* ── Sidebar brand ── */
        .sidebar-brand {
            font-size: 15px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 2px;
        }
        .sidebar-user {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 0;
        }

        /* ── Login Screen ── */
        .login-container {
            text-align: center;
            margin-top: 4rem;
            margin-bottom: 1.5rem;
        }
        .login-logo {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 54px;
            height: 54px;
            background-color: #f0f9ff;
            border-radius: 12px;
            font-size: 24px;
            margin-bottom: 1rem;
            border: 1px solid #e0f2fe;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        .login-title {
            font-size: 26px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.25rem;
        }
        .login-subtitle {
            font-size: 13px;
            color: #64748b;
            margin-bottom: 2rem;
        }
        .login-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 28px;
            box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
            text-align: left;
        }
        .login-card-title {
            font-size: 16px;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 4px;
        }
        .login-card-desc {
            font-size: 12px;
            color: #64748b;
            margin-bottom: 20px;
            line-height: 1.4;
        }

        /* ── Welcome Screen ── */
        .welcome-hero {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 20px;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        }
        .welcome-icon {
            font-size: 28px;
            background: #f0f9ff;
            color: #0284c7;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 52px;
            height: 52px;
            border: 1px solid #e0f2fe;
            flex-shrink: 0;
        }
        .welcome-title {
            font-size: 20px !important;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 2px 0 !important;
        }
        .welcome-subtitle {
            font-size: 13px;
            color: #64748b;
            margin: 0 !important;
            line-height: 1.4;
        }

        /* ── Status Row ── */
        .status-row {
            display: flex;
            gap: 16px;
            flex-wrap: wrap;
            margin-bottom: 28px;
            padding: 0 4px;
        }
        .status-item {
            font-size: 12px;
            color: #475569;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 9999px;
            padding: 4px 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02);
        }
        .status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-dot.green {
            background-color: #10b981;
            box-shadow: 0 0 0 2px #d1fae5;
        }

        /* ── Starter Card overrides ── */
        .starter-card button {
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            padding: 14px 16px !important;
            text-align: left !important;
            width: 100% !important;
            display: block !important;
            box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.02) !important;
            transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
            height: auto !important;
            min-height: 85px !important;
        }
        .starter-card button:hover {
            border-color: #3b82f6 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
            background-color: #ffffff !important;
        }
        .starter-card button p {
            text-align: left !important;
            margin: 0 !important;
            line-height: 1.4 !important;
        }
        </style>
    """, unsafe_allow_html=True)

# Main App Entry
def main():
    inject_custom_styles()
    


    # 3. Handle Session Auth State
    if "user_id" not in st.session_state:
        show_login_screen()
        return

    # Load core singletons.
    db_path = get_db_connection()
    router = QueryRouter(db_path)

    # Initialize active chat session if missing
    if "active_session_id" not in st.session_state or st.session_state.active_session_id is None or "chat_history" not in st.session_state:
        sessions = get_user_chat_sessions(st.session_state.user_id)
        if not sessions:
            active_sid = create_chat_session(st.session_state.user_id, title="Initial Chat")
        else:
            active_sid = sessions[0]["id"]
        st.session_state.active_session_id = active_sid
        raw_hist = get_session_chat_history(st.session_state.user_id, active_sid)
        st.session_state.chat_history = pre_populate_history_metadata(router, raw_hist, st.session_state.user_id)

    # 4. Show Sidebar
    show_sidebar(st.session_state.username, router)

    # 5. Multi-Page Navigation Rendering
    current_page = st.session_state.get("current_page", "💬 AI Chat & RAG")
    
    if current_page == "💬 AI Chat & RAG":
        render_chat_page(router)
    elif current_page == "📊 Quality Dashboard":
        render_dashboard_page(router)
    elif current_page == "📄 Monthly Reports":
        render_reports_page()

def show_login_screen():
    """Renders the passwordless user login screen."""
    st.markdown("""
        <div class="login-container">
            <div class="login-logo">🚗</div>
            <div class="login-title">Automotive QA Intelligence</div>
            <div class="login-subtitle">Offline Technical Diagnostics & Analytics Engine</div>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div class="login-card">
                <div class="login-card-title">Technician Authentication</div>
                <div class="login-card-desc">Enter your username or Technician ID to access the workspace.</div>
        """, unsafe_allow_html=True)
        username = st.text_input("Technician ID / Username")
        login_btn = st.button("Enter Workspace", width="stretch", type="primary")
        
        if login_btn and username.strip():
            user_id = verify_or_create_user(username)
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.username = username.strip()
                st.session_state.last_ingest_check_time = 0.0
                st.session_state.current_page = "💬 AI Chat & RAG"
                
                # Fetch or create session
                sessions = get_user_chat_sessions(user_id)
                if not sessions:
                    active_sid = create_chat_session(user_id, title="Initial Chat")
                else:
                    active_sid = sessions[0]["id"]
                st.session_state.active_session_id = active_sid
                temp_router = QueryRouter(get_db_connection())
                raw_hist = get_session_chat_history(user_id, active_sid)
                st.session_state.chat_history = pre_populate_history_metadata(temp_router, raw_hist, user_id)
                
                st.success("Successfully authenticated!")
                st.rerun()
            else:
                st.error("Authentication error. Please try again.")
        st.markdown("</div>", unsafe_allow_html=True)

def show_sidebar(username, router):
    """Renders the sidebar with navigation, chat threads, and options."""
    with st.sidebar:
        st.markdown(f"<div class='sidebar-brand'>🚗 QA Intelligence</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-user'>Operator: {username}</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # 1. Navigation Panel
        st.markdown("<div class='section-label'>Navigation</div>", unsafe_allow_html=True)
        pages = [
            ("💬 AI Chat & RAG", "💬 AI Chat & RAG"),
            ("📊 Quality Dashboard", "📊 Quality Dashboard"),
            ("📄 Monthly Reports", "📄 Monthly Reports")
        ]
        
        if "current_page" not in st.session_state:
            st.session_state.current_page = "💬 AI Chat & RAG"
            
        for display_name, page_id in pages:
            is_active = st.session_state.current_page == page_id
            btn_type = "primary" if is_active else "secondary"
            if st.button(display_name, key=f"nav_{page_id}", width="stretch", type=btn_type):
                st.session_state.current_page = page_id
                st.rerun()
                
        st.divider()
        
        # 2. Chat Threads / Sessions list
        st.markdown("<div class='section-label'>Conversations</div>", unsafe_allow_html=True)
        
        if st.button("➕ New Chat", width="stretch", type="secondary"):
            new_sid = create_chat_session(st.session_state.user_id, title="New Chat")
            if new_sid:
                st.session_state.active_session_id = new_sid
                st.session_state.chat_history = []
                st.session_state.current_page = "💬 AI Chat & RAG"
                st.rerun()
                
        sessions = get_user_chat_sessions(st.session_state.user_id)
        active_sid = st.session_state.get("active_session_id")
        
        for s in sessions:
            is_active = active_sid == s["id"]
            btn_type = "primary" if is_active else "secondary"
            
            col_sel, col_del = st.columns([6, 1], vertical_alignment="center")
            
            lbl = f"💬 {s['title']}"
            if len(lbl) > 28:
                lbl = lbl[:25] + "..."
                
            if col_sel.button(lbl, key=f"sess_sel_{s['id']}", width="stretch", type=btn_type):
                st.session_state.active_session_id = s["id"]
                raw_hist = get_session_chat_history(st.session_state.user_id, s["id"])
                st.session_state.chat_history = pre_populate_history_metadata(router, raw_hist, st.session_state.user_id)
                st.session_state.current_page = "💬 AI Chat & RAG"
                st.rerun()
                
            if col_del.button("🗑️", key=f"sess_del_{s['id']}", help="Delete chat thread", width="stretch"):
                delete_chat_session(s["id"])
                if active_sid == s["id"]:
                    st.session_state.active_session_id = None
                    st.session_state.chat_history = []
                st.rerun()
                
        st.divider()
        
        # 3. Manual Excel Ingestion Section (Expandable to keep it tidy)
        with st.expander("📥 Manual data ingest", expanded=False):
            st.caption("Drop FTIR Sheets here to parse and index manually.")
            uploaded_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
            if uploaded_file:
                dest_dir = get_inbox_path("data/inbox")
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, uploaded_file.name)
                
                with open(dest_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                    
                st.success(f"Saved to inbox!")
                
            if st.button("🔄 Reload Dataset", type="primary"):
                with st.spinner("Scanning inbox and ingesting datasets..."):
                    files_processed, new_records = scan_and_ingest_inbox()
                st.success(f"Processed {files_processed} files. Ingested {new_records} new records.")
                
        st.divider()
        st.caption("v1.1 · Phi-3 Offline · FAISS Hybrid Search")
        
        # Log out button
        st.markdown("<div class='logout-btn-container'>", unsafe_allow_html=True)
        if st.button("Logout", width="stretch"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def render_citations(citations):
    """Renders visual citation cards for referenced FTIR records."""
    if citations:
        st.markdown("<div style='margin-top: 15px; margin-bottom: 5px; font-weight: 600; font-size: 13px; color: #0369a1;'>📚 Referenced Sources</div>", unsafe_allow_html=True)
        c_cols = st.columns(len(citations) if len(citations) <= 3 else 3)
        for idx, cite in enumerate(citations):
            col_idx = idx % 3
            with c_cols[col_idx]:
                st.markdown(
                    f"""
                    <div class="citation-card">
                        <div style="font-size: 11px; font-weight: bold; color: #0284c7;">FTIR: {cite['ftir_no']}</div>
                        <div style="font-size: 10px; color: #475569; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{cite['subject']}">{cite['subject']}</div>
                        <div style="font-size: 9px; color: #64748b; margin-top: 4px;">{cite['reported_company']} | {cite['outbreak_country']}</div>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

def render_chat_page(router):
    """Renders the Technical Chat and RAG interface."""
    active_sid = st.session_state.get("active_session_id")
    
    # Check if a query is pending (from clicking starter prompt cards)
    query = None
    if st.session_state.get("pending_query"):
        query = st.session_state.pending_query
        del st.session_state["pending_query"]
        
    # Render Welcome Screen if history is empty
    if not st.session_state.chat_history:
        st.markdown("""
            <div class="welcome-hero">
                <div class="welcome-icon">⚡</div>
                <div>
                    <div class="welcome-title">Automotive QA Intelligence</div>
                    <div class="welcome-subtitle">Ask me about specific models, countries, trouble codes, or request quality analytics trends and comparisons.</div>
                </div>
            </div>
            <div class="status-row">
                <div class="status-item"><span class="status-dot green"></span> Database Connected</div>
                <div class="status-item"><span class="status-dot green"></span> FAISS Hybrid Search</div>
                <div class="status-item"><span class="status-dot green"></span> Phi-3 Local LLM</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Starter prompts grid
        st.markdown("<h5 style='color: #475569; margin-bottom: 16px; font-weight: 600; font-size: 14px;'>Suggested Starters</h5>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        starters = [
            ("🔍 Search Incidents", "Find all FTIR reports about transmission failure in US", c1, "start_search"),
            ("📊 DTC Trends", "Show me the trend of DTC complaint codes in 2025", c2, "start_trends"),
            ("📈 Model Compare", "Compare the failure rates of model codes", c3, "start_compare")
        ]
        
        for title, prompt_text, col, key in starters:
            with col:
                st.markdown('<div class="starter-card">', unsafe_allow_html=True)
                if st.button(f"**{title}**\n\n{prompt_text}", key=key, width="stretch"):
                    st.session_state.pending_query = prompt_text
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Title of chat thread
        sessions = get_user_chat_sessions(st.session_state.user_id)
        current_title = next((s["title"] for s in sessions if s["id"] == active_sid), "AI Chat")
        
        col_title, col_export = st.columns([3.5, 1.5], vertical_alignment="center")
        with col_title:
            st.markdown(f"### {current_title}")
            st.caption("Offline Automotive QA Assistant backed by FAISS hybrid retrieval & Phi-3 LLM.")
        with col_export:
            reports_dir = os.path.join(get_project_root(), "reports_cache")
            os.makedirs(reports_dir, exist_ok=True)
            chat_pdf_path = os.path.join(reports_dir, f"Chat_Transcript_{active_sid}.pdf")
            try:
                from reports.engine import ReportEngine
                engine = ReportEngine()
                engine.generate_chat_pdf(current_title, st.session_state.chat_history, st.session_state.username, chat_pdf_path)
                with open(chat_pdf_path, "rb") as f:
                    st.download_button(
                        label="Export Chat PDF 📄",
                        data=f,
                        file_name=f"Chat_Transcript_{active_sid}.pdf",
                        mime="application/pdf",
                        key=f"export_chat_pdf_{active_sid}",
                        width="stretch"
                    )
            except Exception as e:
                st.error(f"Error generating chat PDF: {e}")

    # Render Chat History
    for i, msg in enumerate(st.session_state.chat_history):
        role = msg["role"]
        avatar = "👤" if role == "user" else "✨"
        
        with st.chat_message(role, avatar=avatar):
            if role == "user":
                st.markdown(f"<div style='font-size: 15px;'>{msg['content']}</div>", unsafe_allow_html=True)
            else: # assistant
                user_query = st.session_state.chat_history[i-1]["content"] if (i > 0 and st.session_state.chat_history[i-1]["role"] == "user") else None
                
                intent = msg.get("intent")
                if intent:
                    badge_class = f"badge-{intent.lower().replace('+', '_')}"
                    st.markdown(f"<span class='intent-badge {badge_class}'>{intent}</span>", unsafe_allow_html=True)
                
                is_visual = msg.get("is_visual", False)
                res_type = msg.get("res_type")
                df = msg.get("df")
                sql_query = msg.get("sql_query")
                chart_type = msg.get("chart_type")
                chart_title = msg.get("chart_title")
                citations = msg.get("citations")
                
                if user_query and is_visual:
                    if sql_query:
                        with st.expander("🔍 SQL Query Used", expanded=False):
                            st.code(sql_query, language="sql")
                    if df is not None:
                        st.dataframe(df, width="stretch")
                    if chart_type and chart_type != "empty" and df is not None:
                        render_plotly_chart(chart_type, df, chart_title, key=f"hist_{i}_{chart_type}")
                        
                    if res_type == "table_stream":
                        st.markdown("**Analysis Explanation:**")
                    st.write(msg["content"])
                    
                    if res_type == "report" and msg.get("report_data"):
                        rd = msg["report_data"]
                        ryear = rd.get("year")
                        rmonth = rd.get("month")
                        reports_dir = os.path.join(get_project_root(), "reports_cache")
                        pdf_path = os.path.join(reports_dir, f"QA_Report_{ryear}_{rmonth}.pdf")
                        docx_path = os.path.join(reports_dir, f"QA_Report_{ryear}_{rmonth}.docx")
                        if not (os.path.exists(pdf_path) and os.path.exists(docx_path)):
                            from reports.engine import ReportEngine
                            os.makedirs(reports_dir, exist_ok=True)
                            engine = ReportEngine()
                            engine.generate_pdf_report(ryear, rmonth, pdf_path)
                            engine.generate_docx_report(ryear, rmonth, docx_path)
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label="Download PDF Report 📄",
                                    data=f,
                                    file_name=f"QA_Report_{ryear}_{rmonth}.pdf",
                                    mime="application/pdf",
                                    key=f"hist_pdf_{i}_{ryear}_{rmonth}",
                                    width="stretch"
                                )
                        with c2:
                            with open(docx_path, "rb") as f:
                                st.download_button(
                                    label="Download DOCX Report 📝",
                                    data=f,
                                    file_name=f"QA_Report_{ryear}_{rmonth}.docx",
                                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    key=f"hist_docx_{i}_{ryear}_{rmonth}",
                                    width="stretch"
                                )
                                
                    render_citations(citations)
                else:
                    st.write(msg["content"])
                    render_citations(citations)

    # Chat Input
    input_query = st.chat_input("Ask a question about model failures, trouble codes, or repair success...")
    if input_query:
        query = input_query
        
    if query:
        # Display user message
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"<div style='margin-bottom:10px; font-size: 15px;'>{query}</div>", unsafe_allow_html=True)
            
        # Update session title if first query
        user_messages_count = sum(1 for m in st.session_state.chat_history if m["role"] == "user")
        if user_messages_count == 0 and active_sid:
            sessions = get_user_chat_sessions(st.session_state.user_id)
            current_title = next((s["title"] for s in sessions if s["id"] == active_sid), "New Chat")
            if current_title == "New Chat":
                new_title = query[:25] + "..." if len(query) > 25 else query
                update_chat_session_title(active_sid, new_title)
            
        # Append to DB and session history
        add_chat_message(st.session_state.user_id, active_sid, "user", query)
        st.session_state.chat_history.append({"role": "user", "content": query})
        
        # Execute query dispatch
        with st.chat_message("assistant", avatar="✨"):
            router_res = router.dispatch_query(query, user_id=st.session_state.user_id)
            intent = router_res["intent"]
            res_type = router_res["type"]
            citations = router_res["citations"]
            
            # Show Intent Badge
            badge_class = f"badge-{intent.lower().replace('+', '_')}"
            st.markdown(f"<span class='intent-badge {badge_class}'>{intent}</span>", unsafe_allow_html=True)
            
            response_text = ""
            extracted_df = None
            
            # Handle Text Streams
            if res_type == "text_stream":
                messages = router_res["data"]
                if isinstance(messages, list) and isinstance(messages[0], str):
                    st.write(messages[0])
                    response_text = messages[0]
                else:
                    llm_client = get_llm()
                    response_text = st.write_stream(llm_client.generate_chat_stream(messages))
                    
            # Handle Table Streams
            elif res_type == "table_stream":
                df = router_res["data"]["df"]
                extracted_df = df
                messages = router_res["data"]["messages"]
                
                if router_res.get("sql_query"):
                    with st.expander("🔍 SQL Query Used", expanded=False):
                        st.code(router_res["sql_query"], language="sql")
                st.dataframe(df, width="stretch")
                
                chart_type = router_res["chart_type"]
                chart_title = router_res["chart_title"]
                if chart_type and chart_type != "empty":
                    render_plotly_chart(chart_type, df, chart_title, key=f"new_stream_{int(time.time())}_{chart_type}")
                    
                st.markdown("**Analysis Explanation:**")
                llm_client = get_llm()
                response_text = st.write_stream(llm_client.generate_chat_stream(messages))
                
            # Handle Table Only
            elif res_type == "table_only":
                df = router_res["data"]
                extracted_df = df
                if router_res.get("sql_query"):
                    with st.expander("🔍 SQL Query Used", expanded=False):
                        st.code(router_res["sql_query"], language="sql")
                st.dataframe(df, width="stretch")
                
                chart_type = router_res["chart_type"]
                chart_title = router_res["chart_title"]
                if chart_type and chart_type != "empty":
                    render_plotly_chart(chart_type, df, chart_title, key=f"new_only_{int(time.time())}_{chart_type}")
                    
                response_text = f"Displayed analytics table: {chart_title}"
                st.write(response_text)
                
            # Handle Report Generation
            elif res_type == "report":
                year = router_res["data"]["year"]
                month = router_res["data"]["month"]
                
                from reports.engine import ReportEngine
                reports_dir = os.path.join(get_project_root(), "reports_cache")
                os.makedirs(reports_dir, exist_ok=True)
                pdf_path = os.path.join(reports_dir, f"QA_Report_{year}_{month}.pdf")
                docx_path = os.path.join(reports_dir, f"QA_Report_{year}_{month}.docx")
                
                engine = ReportEngine()
                with st.spinner(f"Compiling database records and generating reports..."):
                    engine.generate_pdf_report(year, month, pdf_path)
                    engine.generate_docx_report(year, month, docx_path)
                
                month_name = datetime.date(1900, month, 1).strftime('%B')
                response_text = f"Successfully generated QA Quality Reports for {month_name} {year}. Click the buttons below to download."
                st.write(response_text)
                
                c1, c2 = st.columns(2)
                with c1:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            label="Download PDF Report 📄",
                            data=f,
                            file_name=f"QA_Report_{year}_{month}.pdf",
                            mime="application/pdf",
                            key=f"report_pdf_{int(time.time())}",
                            width="stretch"
                        )
                with c2:
                    with open(docx_path, "rb") as f:
                        st.download_button(
                            label="Download DOCX Report 📝",
                            data=f,
                            file_name=f"QA_Report_{year}_{month}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"report_docx_{int(time.time())}",
                            width="stretch"
                        )
                
            # Save response to history and DB
            add_chat_message(st.session_state.user_id, active_sid, "assistant", response_text)
            
            history_entry = {
                "role": "assistant",
                "content": response_text,
                "is_visual": res_type in ("table_only", "table_stream", "report", "escalation"),
                "res_type": res_type,
                "df": extracted_df,
                "report_data": router_res.get("data") if res_type == "report" else None,
                "intent": intent,
                "sql_query": router_res.get("sql_query"),
                "chart_type": router_res.get("chart_type"),
                "chart_title": router_res.get("chart_title"),
                "citations": citations
            }
            st.session_state.chat_history.append(history_entry)
            
            # Render Expandable Citations
            render_citations(citations)
                        
            # Cache the result for the query
            router_res["generated_response"] = response_text
            router.cache.set(query, st.session_state.user_id, router_res)
                
        # Force refresh to update sidebar title
        st.rerun()


def pre_populate_history_metadata(router, history, user_id):
    """
    Runs once when history is loaded. Iterates over history, checks if assistant responses
    were visual, and loads their details from cache without re-running LLM.
    """
    for i, msg in enumerate(history):
        if msg["role"] == "assistant":
            if "is_visual" in msg:
                continue
                
            user_query = history[i-1]["content"] if (i > 0 and history[i-1]["role"] == "user") else None
            if user_query:
                intent, _ = router.nlp.classify_intent(user_query)
                msg["intent"] = intent
                is_visual = intent in ("ANALYTICS", "VISUALIZE", "VISUALIZE+EXPLAIN", "COMPARE", "ESCALATION")
                
                if is_visual or intent == "SEARCH":
                    try:
                        router_res = router.dispatch_query(user_query, user_id=user_id)
                        res_type = router_res["type"]
                        msg["is_visual"] = res_type in ("table_only", "table_stream", "report", "escalation")
                        msg["res_type"] = res_type
                        if res_type == "table_only":
                            msg["df"] = router_res["data"]
                        elif res_type == "table_stream":
                            msg["df"] = router_res["data"]["df"]
                        elif res_type == "report":
                            msg["df"] = None
                            msg["report_data"] = router_res["data"]
                        else:
                            msg["df"] = None
                        msg["sql_query"] = router_res.get("sql_query")
                        msg["chart_type"] = router_res.get("chart_type")
                        msg["chart_title"] = router_res.get("chart_title")
                        msg["citations"] = router_res.get("citations")
                    except Exception as e:
                        print(f"Error pre-populating history item: {e}")
            if "is_visual" not in msg:
                msg["is_visual"] = False
    return history

def render_plotly_chart(chart_type, df, title, key=None):
    """Renders the appropriate Plotly figure based on the selector type."""
    fig = None
    if chart_type == "horizontal_bar":
        fig = plot_horizontal_bar(df, df.columns[1], df.columns[0], title)
    elif chart_type == "line":
        # Usually the x_axis is 'period' or the first column, other columns are y_cols
        x_col = "period" if "period" in df.columns else df.columns[0]
        y_cols = [c for c in df.columns if c not in [x_col, "report_year", "report_month"]]
        fig = plot_line_trend(df, x_col, y_cols, title)
    elif chart_type == "donut":
        fig = plot_donut_chart(df, df.columns[0], df.columns[1], title)
    elif chart_type == "histogram":
        fig = plot_histogram(df, df.columns[0], title)
    elif chart_type == "radar":
        fig = plot_radar_comparison(df, df.columns[0], list(df.columns[1:4]), title)
    elif chart_type == "grouped_bar":
        fig = plot_grouped_bar(df, df.columns[0], list(df.columns[1:]), title)
        
    if fig:
        st.plotly_chart(fig, width="stretch", key=key)

def render_dashboard_page(router):
    """Renders the comprehensive quality stats dashboard page."""
    st.markdown("### Quality Analytics Dashboard")
    st.caption("Pre-aggregated metrics loaded directly from SQLite materialized view tables.")
    
    # Render top metric cards
    col1, col2, col3, col4 = st.columns(4)
    conn = sqlite3.connect(router.db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM records;")
    total_records = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT product_model_code) FROM records;")
    total_models = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT reported_company) FROM records;")
    total_dealers = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM records WHERE is_resolved = 1;")
    resolved_claims = cursor.fetchone()[0]
    
    conn.close()

    with col1:
        st.markdown(f"<div class='metric-card-blue'><div class='metric-label'>Total FTIR Records</div><div class='metric-value'>{total_records}</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-card-teal'><div class='metric-label'>Product Models</div><div class='metric-value'>{total_models}</div></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div class='metric-card-amber'><div class='metric-label'>Active Dealers</div><div class='metric-value'>{total_dealers}</div></div>", unsafe_allow_html=True)
    with col4:
        st.markdown(f"<div class='metric-card-emerald'><div class='metric-label'>Resolved Claims</div><div class='metric-value'>{resolved_claims} <span style='font-size:14px;color:#059669;'>({(resolved_claims*100/total_records):.1f}%)</span></div></div>", unsafe_allow_html=True)

    # Load 4 major charts in 2x2 grid
    c1, c2 = st.columns(2)
    with c1:
        df_tc, _ = router.analytics_engine.get_trouble_code_frequency(limit=10)
        fig_tc = plot_horizontal_bar(df_tc, 'count', 'trouble_code', "Top Trouble Codes by Claims Count")
        st.plotly_chart(fig_tc, width="stretch")
        
        df_qual, _ = router.analytics_engine.get_quality_distribution()
        fig_qual = plot_donut_chart(df_qual, 'quality', 'count', "Quality Ratings Distribution")
        st.plotly_chart(fig_qual, width="stretch")
        
    with c2:
        df_trend, _ = router.analytics_engine.get_monthly_failure_trend()
        fig_trend = plot_line_trend(df_trend, 'period', 'failures', "Chronological Claims Trend")
        st.plotly_chart(fig_trend, width="stretch")
        
        st.markdown("#### Model Performance Comparison")
        df_comp, _ = router.analytics_engine.get_model_comparison()
        st.dataframe(df_comp, width="stretch", height=280)

def render_escalation_page(router):
    """Renders the escalations page (Poor quality AND Unresolved)."""
    st.markdown("### Unresolved Escalation Dashboard")
    st.caption("Active quality cases flagged as 'Poor' quality where issue is not resolved. SQL-only, no LLM.")

    df_esc, _ = router.analytics_engine.get_escalations()
    if df_esc.empty:
        st.success("No active escalations. All poor quality cases resolved! 🎉")
    else:
        st.warning(f"Found {len(df_esc)} critical escalations requiring priority management.")
        st.dataframe(df_esc, width="stretch")

def render_reports_page():
    """Renders the monthly PDF/DOCX generation tab."""
    st.markdown("### Executive Quality Reports")
    st.caption("Select the month and year to compile a formatted PDF and Word report.")
    
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Select Year:", [2024, 2025, 2026], index=1)
        month = st.selectbox(
            "Select Month:", 
            list(range(1, 13)), 
            format_func=lambda x: datetime.date(1900, x, 1).strftime('%B'),
            index=11
        )
        
    with col2:
        st.markdown("<br/>", unsafe_allow_html=True)
        generate_btn = st.button("Generate Reports", type="primary", width="stretch")

    if generate_btn:
        from reports.engine import ReportEngine
        reports_dir = os.path.join(get_project_root(), "reports_cache")
        os.makedirs(reports_dir, exist_ok=True)
        pdf_path = os.path.join(reports_dir, f"QA_Report_{year}_{month}.pdf")
        docx_path = os.path.join(reports_dir, f"QA_Report_{year}_{month}.docx")
        
        engine = ReportEngine()
        
        with st.spinner("Compiling database records and generating reports..."):
            engine.generate_pdf_report(year, month, pdf_path)
            engine.generate_docx_report(year, month, docx_path)
            
        st.success("Reports generated successfully!")
        
        c1, c2 = st.columns(2)
        with c1:
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="Download PDF Report 📄",
                    data=f,
                    file_name=f"QA_Report_{year}_{month}.pdf",
                    mime="application/pdf",
                    width="stretch"
                )
        with c2:
            with open(docx_path, "rb") as f:
                st.download_button(
                    label="Download DOCX Report 📝",
                    data=f,
                    file_name=f"QA_Report_{year}_{month}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    width="stretch"
                )

if __name__ == "__main__":
    main()
