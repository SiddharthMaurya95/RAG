import os
import sys
import time
import datetime
import threading
import sqlite3
import streamlit as st
import pandas as pd

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.logger import get_logger
from core.custom_exception import CustomException

logger = get_logger(__name__)

# Import local modules
import importlib
for mod in ["core.memory.session", "core.singletons", "core.pipeline", "core.paths", "core.utils.charts", "core.utils.report_engine", "core.sql.sql_executor", "core.agents.visualization_agent", "core.engine.intent.nlp", "core.ollama_client"]:
    if mod in sys.modules:
        try:
            importlib.reload(sys.modules[mod])
        except Exception:
            pass

from core.memory.session import (
    verify_or_create_user, 
    get_user_chat_history, 
    add_chat_message,
    create_chat_session,
    get_user_chat_sessions,
    get_session_chat_history,
    update_chat_session_title,
    delete_chat_session,
    delete_chat_message
)
from core.singletons import get_db_connection, get_embedder, get_llm, get_ingestion_tracker, get_router
from core.pipeline import QueryRouter
from core.paths import get_inbox_path, get_project_root
from core.utils.ui_utils import inject_design_system, render_app_header
from core.utils.charts import (
    plot_horizontal_bar, 
    plot_line_trend, 
    plot_donut_chart, 
    plot_histogram, 
    plot_radar_comparison,
    plot_grouped_bar,
    plot_scatter_plot,
    plot_box_plot,
    plot_violin_plot,
    plot_area_chart
)

MAX_FRONTEND_ROWS = 100000

@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

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
        .stAppDeployButton, .stDeployButton, [data-testid="stAppDeployButton"], [data-testid="stToolbar"] {
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

        /* Centered cross mark delete buttons with padding/margin */
        [data-testid="stSidebar"] div[data-testid="column"]:nth-child(2) button {
            width: 100% !important;
            min-width: 0 !important;
            margin: 0 auto !important;
            padding: 4px !important;
            min-height: 32px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-sizing: border-box !important;
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
            margin-left: auto !important;
            margin-right: auto !important;
            display: flex;
            justify-content: center;
        }

        /* ── Chart container ── */
        .chart-container {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 12px 8px 4px 8px;
            margin-bottom: 16px;
            margin-left: auto !important;
            margin-right: auto !important;
            display: flex;
            justify-content: center;
        }

        [data-testid="stPlotlyChart"] {
            margin-left: auto !important;
            margin-right: auto !important;
            display: flex;
            justify-content: center;
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
    # Start the background Inbox Watcher once per Python process session
    if "watcher_started" not in st.session_state:
        st.session_state.watcher_started = True
        try:
            from core.etl.watcher import start_inbox_watcher
            start_inbox_watcher()
        except Exception:
            pass

    # Inject styles only once per browser session to avoid re-injecting the large
    # CSS block on every Streamlit rerun (keystroke, token stream, etc.)
    if "styles_injected" not in st.session_state:
        inject_custom_styles()
        st.session_state.styles_injected = True

    # Inject enterprise design system CSS
    inject_design_system()

    # Eagerly warm up the LLM on startup
    if "llm_warmed_up" not in st.session_state:
        st.session_state.llm_warmed_up = True
        from core.singletons import get_llm
        get_llm()

    # 3. Handle Session Auth State
    if "user_id" not in st.session_state:
        # Hide Streamlit's default header and remove top padding only on the login screen
        st.markdown("""
            <style>
            header[data-testid="stHeader"] { display: none !important; }
            [data-testid="stAppViewBlockContainer"], .stMainBlockContainer, .block-container { padding-top: 0 !important; }
            </style>
        """, unsafe_allow_html=True)
        # Render the custom brand header bar ONLY on the login screen
        render_app_header()
        show_login_screen()
        return

    # Render the AI warning at the bottom on every rerun when logged in
    st.markdown('<div class="ai-warning">This system uses AI and can make mistakes.</div>', unsafe_allow_html=True)

    # Check for background auto-ingestion events
    tracker = get_ingestion_tracker()
    if tracker.last_ingest_time > 0.0:
        last_check = st.session_state.get("last_ingest_check_time", 0.0)
        if tracker.last_ingest_time > last_check:
            st.session_state.last_ingest_check_time = tracker.last_ingest_time
            st.toast(f"📥 Automatically ingested `{tracker.new_records_count}` records from inbox file: `{tracker.last_ingested_file}`", icon="✅")

    # Load core singletons.
    db_path = get_db_connection()
    router = get_router(db_path)
    
    # Self-healing cache clear if QueryRouter definition is out-of-sync
    import inspect
    if "chat_history" not in inspect.signature(router.dispatch_query).parameters:
        st.cache_resource.clear()
        st.rerun()

    # Fetch the session list once per rerun and share it between main(), show_sidebar(),
    # and render_chat_page() to eliminate redundant repeated DB queries.
    user_sessions = get_user_chat_sessions(st.session_state.user_id)

    # Initialize active chat session if missing
    if "active_session_id" not in st.session_state or st.session_state.active_session_id is None or "chat_history" not in st.session_state:
        sessions = user_sessions
        if not sessions:
            active_sid = create_chat_session(st.session_state.user_id, title="Initial Chat")
        else:
            active_sid = sessions[0]["id"]
        st.session_state.active_session_id = active_sid
        raw_hist = get_session_chat_history(st.session_state.user_id, active_sid)
        st.session_state.chat_history = pre_populate_history_metadata(router, raw_hist, st.session_state.user_id)

    # 4. Show Sidebar
    show_sidebar(st.session_state.username, router, user_sessions)

    # 5. Multi-Page Navigation Rendering
    render_chat_page(router)


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
        
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Technician ID / Username", placeholder="👤 Enter Technician ID or Username")
            login_btn = st.form_submit_button("Enter Workspace", use_container_width=True, type="primary")
            
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


def show_sidebar(username, router, user_sessions=None):
    """Renders the sidebar with navigation, chat threads, and options."""
    with st.sidebar:
        st.markdown(f"<div class='sidebar-brand'>🚗 QA Intelligence</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sidebar-user'>Operator: {username}</div>", unsafe_allow_html=True)
        
        st.divider()
        
        # 2. Chat Threads / Sessions list
        st.markdown("<div class='section-label'>Conversations</div>", unsafe_allow_html=True)
        
        if st.button("➕ New Chat", width="stretch", type="secondary"):
            new_sid = create_chat_session(st.session_state.user_id, title="New Chat")
            if new_sid:
                st.session_state.active_session_id = new_sid
                st.session_state.active_session_title = "New Chat"
                st.session_state.chat_history = []
                st.session_state.current_page = "💬 AI Chat & RAG"
                st.rerun()
                
        if "deleted_session_ids" not in st.session_state:
            st.session_state.deleted_session_ids = set()

        # Use the pre-fetched sessions list passed from main() to avoid a redundant DB query
        raw_sessions = user_sessions if user_sessions is not None else get_user_chat_sessions(st.session_state.user_id)
        sessions = [s for s in raw_sessions if s["id"] not in st.session_state.deleted_session_ids]
        active_sid = st.session_state.get("active_session_id")
        
        for s in sessions:
            is_active = active_sid == s["id"]
            btn_type = "primary" if is_active else "secondary"
            
            col_sel, col_del = st.columns([4, 1], vertical_alignment="center")
            
            lbl = f"💬 {s['title']}"
            if len(lbl) > 28:
                lbl = lbl[:25] + "..."
                
            if col_sel.button(lbl, key=f"sess_sel_{s['id']}", width="stretch", type=btn_type):
                st.session_state.active_session_id = s["id"]
                st.session_state.active_session_title = s["title"]
                raw_hist = get_session_chat_history(st.session_state.user_id, s["id"])
                st.session_state.chat_history = pre_populate_history_metadata(router, raw_hist, st.session_state.user_id)
                st.session_state.current_page = "💬 AI Chat & RAG"
                st.rerun()
                
            if col_del.button("❌", key=f"sess_del_{s['id']}", help="Delete chat thread", use_container_width=True):
                st.session_state.deleted_session_ids.add(s["id"])
                if active_sid == s["id"]:
                    st.session_state.active_session_id = None
                    st.session_state.chat_history = []
                # Run the actual database deletion task in a background daemon thread
                import threading
                threading.Thread(target=delete_chat_session, args=(s["id"],), daemon=True).start()
                st.rerun()
                
        # 3. LLM Configuration (Silent Sync)
        llm_client = get_llm()
        
        # Caption status
        st.caption("v1.3 · Offline LLM · FAISS Hybrid")
        
        # Log out button
        st.markdown("<div class='logout-btn-container'>", unsafe_allow_html=True)
        if st.button("Logout", width="stretch"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def render_citations(citations):
    """Renders visual citation cards for referenced FTIR records. Disabled as per user request."""
    return

@st.dialog("Select Query Routing Intent")
def select_intent_dialog():
    st.write("Force a specific query classification or let the system dynamically route it.")
    
    options = [
        "Use Previous / Default",
        "ANALYTICS",
        "SEARCH"
    ]
    current = st.session_state.get("selected_intent", "Use Previous / Default")
    default_idx = options.index(current) if current in options else 0
    
    chosen = st.radio(
        "Choose intent routing option:",
        options,
        index=default_idx
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Apply", type="primary", width="stretch"):
            st.session_state.selected_intent = chosen
            st.rerun()
    with col2:
        if st.button("Cancel", width="stretch"):
            st.rerun()

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
            <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 3rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); text-align: center; color: white;">
                <div style="font-size: 2.75rem; margin-bottom: 1rem;">🛡️</div>
                <h1 style="color: #f8fafc; font-size: 2.25rem; font-weight: 700; margin-bottom: 1rem; letter-spacing: -0.025em; border: none; padding: 0;">Automotive QA Intelligence System</h1>
                <p style="color: #cbd5e1; font-size: 1.1rem; max-width: 700px; margin: 0 auto; line-height: 1.6;">
                    Enterprise technical diagnostics and analytics engine. Query historical defect reports, investigate complex trouble codes, and conduct cross-market quality comparisons.
                </p>
            </div>
            
            <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 2rem; margin-bottom: 3.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem; color: #475569; font-size: 0.95rem; font-weight: 500;"><span style="display: inline-block; width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 0 2px #d1fae5;"></span> Secure Database Connected</div>
                <div style="display: flex; align-items: center; gap: 0.5rem; color: #475569; font-size: 0.95rem; font-weight: 500;"><span style="display: inline-block; width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 0 2px #d1fae5;"></span> FAISS Hybrid Search Active</div>
                <div style="display: flex; align-items: center; gap: 0.5rem; color: #475569; font-size: 0.95rem; font-weight: 500;"><span style="display: inline-block; width: 8px; height: 8px; background-color: #10b981; border-radius: 50%; box-shadow: 0 0 0 2px #d1fae5;"></span> Neural Engine Online</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Starter prompts grid
        st.markdown("<h4 style='color: #0f172a; text-align: center; margin-bottom: 1.5rem; font-weight: 600; font-size: 1.25rem; letter-spacing: -0.025em;'>Recommended Analytical Workflows</h4>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        starters = [
            ("📊 Component Failure Graph", "give top 10 failed parts with reasons on graph", c1, "start_search"),
            ("🔍 Critical Quality Matrix", "Show a bar chart of all outbreak_country", c2, "start_trends"),
            ("📄 Global Incident Log", "Show a table of the ftir_no and reported_country", c3, "start_compare")
        ]
        
        for title, prompt_text, col, key in starters:
            with col:
                st.markdown('<div class="starter-card">', unsafe_allow_html=True)
                if st.button(f"**{title}**\n\n{prompt_text}", key=key, width="stretch"):
                    st.session_state.pending_query = prompt_text
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Derive current thread title from session state if possible to avoid a DB query
        active_sid = st.session_state.get("active_session_id")
        current_title = st.session_state.get("active_session_title", "AI Chat")
        
        st.caption("Offline Automotive QA Assistant backed by FAISS hybrid retrieval & Offline LLM.")

    # Render Chat History
    # Clean up any orphaned user message at the end of the history (if generation was interrupted)
    if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        orphaned_msg = st.session_state.chat_history.pop()
        msg_id = orphaned_msg.get("id")
        if msg_id:
            delete_chat_message(msg_id)

    for i, msg in enumerate(st.session_state.chat_history):
        role = msg["role"]
        avatar = "👤" if role == "user" else "✨"
        
        with st.chat_message(role, avatar=avatar):
            if role == "user":
                col_text, col_del = st.columns([9.5, 0.5])
                with col_text:
                    st.markdown(f"<div style='font-size: 15px;'>{msg['content']}</div>", unsafe_allow_html=True)
                with col_del:
                    msg_id = msg.get("id")
                    if msg_id:
                        if st.button("❌", key=f"del_msg_{msg_id}_{i}", help="Delete query", use_container_width=True):
                            # Collect IDs to delete
                            ids_to_delete = {msg_id}
                            # Also delete corresponding assistant response if it exists
                            if i + 1 < len(st.session_state.chat_history):
                                next_msg = st.session_state.chat_history[i+1]
                                if next_msg["role"] == "assistant":
                                    next_id = next_msg.get("id")
                                    if next_id:
                                        ids_to_delete.add(next_id)
                            # Delete from DB
                            for mid in ids_to_delete:
                                delete_chat_message(mid)
                            # Remove from session_state in-place — do NOT call pre_populate
                            # (pre_populate re-dispatches queries through the router/LLM and causes crashes)
                            st.session_state.chat_history = [
                                m for m in st.session_state.chat_history
                                if m.get("id") not in ids_to_delete
                            ]
                            st.session_state[f"pdf_ready_{active_sid}"] = False
                            st.rerun()
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
                chart_data = msg.get("chart_data")
                citations = msg.get("citations")
                
                if user_query and is_visual:
                    if sql_query:
                        with st.expander("🔍 SQL Query Used", expanded=False):
                            st.code(sql_query, language="sql")
                    if df is not None:
                        if len(df) > MAX_FRONTEND_ROWS:
                            st.info(f"⚠️ Showing top {MAX_FRONTEND_ROWS} rows of {len(df)} total results.")
                            csv_data = convert_df_to_csv(df)
                            st.download_button(
                                label="📥 Download Full Results (CSV)",
                                data=csv_data,
                                file_name="query_results.csv",
                                mime="text/csv",
                                key=f"dl_hist_{i}_{int(time.time())}"
                            )
                            st.dataframe(df.head(MAX_FRONTEND_ROWS), width="stretch")
                        else:
                            st.dataframe(df, width="stretch")
                    if chart_type and chart_type != "empty":
                        c_df = chart_data if chart_data is not None else df
                        if c_df is not None:
                            render_plotly_chart(chart_type, c_df, chart_title, key=f"hist_{i}_{chart_type}")
                        
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
                    if msg.get("sql_query"):
                        with st.expander("🔍 SQL Query Used", expanded=False):
                            st.code(msg["sql_query"], language="sql")
                    st.write(msg["content"])
                    render_citations(citations)

    # Intent Selector Button and Status
    selected_intent = st.session_state.get("selected_intent", "Use Previous / Default")
    
    col_status, col_btn = st.columns([7, 3], vertical_alignment="center")
    with col_status:
        if selected_intent == "Use Previous / Default":
            prev_intent = None
            for msg in reversed(st.session_state.chat_history):
                if msg["role"] == "assistant" and msg.get("intent"):
                    prev_intent = msg["intent"]
                    break
            if prev_intent:
                st.caption(f"Routing Intent Mode: 🔄 **Previous ({prev_intent})**")
            else:
                st.caption("Routing Intent Mode: 🤖 **ANALYTICS (Default)**")
        else:
            st.caption(f"Routing Intent Mode: ⚙️ **{selected_intent}**")
            
    with col_btn:
        if st.button("⚙️ Select Routing Intent", key="routing_intent_btn", width="stretch"):
            select_intent_dialog()

    # Chat Input
    input_query = st.chat_input("Ask a question about model failures, trouble codes, or repair success...")
    if input_query:
        query = input_query
        st.session_state[f"pdf_ready_{active_sid}"] = False
        
    if query:
        # Update session title if first query — use session state to avoid a DB query
        user_messages_count = sum(1 for m in st.session_state.chat_history if m["role"] == "user")
        if user_messages_count == 0 and active_sid:
            current_title = st.session_state.get("active_session_title", "New Chat")
            if current_title == "New Chat":
                new_title = query[:25] + "..." if len(query) > 25 else query
                update_chat_session_title(active_sid, new_title)
                st.session_state.active_session_title = new_title
            
        # Append to DB and session history BEFORE rendering so we have the msg_id
        user_msg_id = add_chat_message(st.session_state.user_id, active_sid, "user", query)
        st.session_state.chat_history.append({"id": user_msg_id, "role": "user", "content": query})

        # Display user message with the delete button
        with st.chat_message("user", avatar="👤"):
            col_text, col_del = st.columns([9.5, 0.5])
            with col_text:
                st.markdown(f"<div style='margin-bottom:10px; font-size: 15px;'>{query}</div>", unsafe_allow_html=True)
            with col_del:
                if st.button("❌", key=f"del_active_{user_msg_id}", help="Delete query and stop generation", use_container_width=True):
                    # User clicked delete during generation
                    delete_chat_message(user_msg_id)
                    st.session_state.chat_history = [
                        m for m in st.session_state.chat_history
                        if m.get("id") != user_msg_id
                    ]
                    st.rerun()
        
        # Determine override intent
        override_intent = st.session_state.get("selected_intent", "Use Previous / Default")
        if override_intent == "Use Previous / Default":
            previous_intent = None
            for msg in reversed(st.session_state.chat_history):
                if msg["role"] == "assistant" and msg.get("intent"):
                    previous_intent = msg["intent"]
                    break
            override_intent = previous_intent

        # RAG configuration is set to 0.1 as requested
        threshold_val = 0.2
        # Execute query dispatch
        with st.chat_message("assistant", avatar="✨"):
            router_res = router.dispatch_query(
                query, 
                user_id=st.session_state.user_id,
                override_intent=override_intent,
                threshold=threshold_val,
                chat_history=st.session_state.chat_history
            )
            intent = router_res["intent"]
            res_type = router_res["type"]
            citations = router_res["citations"]
            
            # Show Intent Badge
            badge_class = f"badge-{intent.lower().replace('+', '_')}"
            st.markdown(f"<span class='intent-badge {badge_class}'>{intent}</span>", unsafe_allow_html=True)
            
            # Reset values for output
            response_text = ""
            extracted_df = None
            
            # Handle Text Streams
            if res_type == "text_stream":
                if router_res.get("sql_query"):
                    with st.expander("🔍 SQL Query Used", expanded=False):
                        st.code(router_res["sql_query"], language="sql")
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
                if len(df) > MAX_FRONTEND_ROWS:
                    st.info(f"⚠️ Showing top {MAX_FRONTEND_ROWS} rows of {len(df)} total results.")
                    csv_data = convert_df_to_csv(df)
                    st.download_button(
                        label="📥 Download Full Results (CSV)",
                        data=csv_data,
                        file_name="query_results.csv",
                        mime="text/csv",
                        key=f"dl_stream_{int(time.time())}"
                    )
                    st.dataframe(df.head(MAX_FRONTEND_ROWS), width="stretch")
                else:
                    st.dataframe(df, width="stretch")
                
                chart_type = router_res.get("chart_type")
                chart_title = router_res.get("chart_title")
                chart_df = router_res.get("chart_data")
                if chart_df is None:
                    chart_df = df
                    
                if chart_type and chart_type != "empty":
                    render_plotly_chart(chart_type, chart_df, chart_title, key=f"new_stream_{int(time.time())}_{chart_type}")
                    
                st.markdown("**Analysis Explanation:**")
                import types
                if isinstance(messages, str):
                    st.write(messages)
                    response_text = messages
                elif isinstance(messages, types.GeneratorType):
                    response_text = st.write_stream(messages)
                else:
                    llm_client = get_llm()
                    response_text = st.write_stream(llm_client.generate_chat_stream(messages))
                
            # Handle Table Only
            elif res_type == "table_only":
                df = router_res["data"]
                extracted_df = df
                if router_res.get("sql_query"):
                    with st.expander("🔍 SQL Query Used", expanded=False):
                        st.code(router_res["sql_query"], language="sql")
                if len(df) > MAX_FRONTEND_ROWS:
                    st.info(f"⚠️ Showing top {MAX_FRONTEND_ROWS} rows of {len(df)} total results.")
                    csv_data = convert_df_to_csv(df)
                    st.download_button(
                        label="📥 Download Full Results (CSV)",
                        data=csv_data,
                        file_name="query_results.csv",
                        mime="text/csv",
                        key=f"dl_only_{int(time.time())}"
                    )
                    st.dataframe(df.head(MAX_FRONTEND_ROWS), width="stretch")
                else:
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
            assistant_msg_id = add_chat_message(st.session_state.user_id, active_sid, "assistant", response_text, intent=intent)
            
            history_entry = {
                "id": assistant_msg_id,
                "role": "assistant",
                "content": response_text,
                "is_visual": res_type in ("table_only", "table_stream", "report"),
                "res_type": res_type,
                "df": extracted_df,
                "report_data": router_res.get("data") if res_type == "report" else None,
                "intent": intent,
                "sql_query": router_res.get("sql_query"),
                "chart_type": router_res.get("chart_type"),
                "chart_title": router_res.get("chart_title"),
                "chart_data": router_res.get("chart_data"),
                "citations": citations,
                "threshold_used": router_res.get("threshold_used"),
                "row_count": router_res.get("row_count"),
                "score_range": router_res.get("score_range"),
                "scores_list": router_res.get("scores_list")
            }
            st.session_state.chat_history.append(history_entry)
            
            # Render Expandable Citations
            render_citations(citations)
                        
            # Cache the result for the query if it is not an error or fallback message
            if "An error occurred" not in response_text and "No sufficiently similar" not in response_text:
                router_res["generated_response"] = response_text
                if "data" in router_res and isinstance(router_res["data"], dict) and "messages" in router_res["data"]:
                    router_res["data"]["messages"] = response_text
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
                # If intent was saved in database, use it directly to preserve overrides
                if msg.get("intent"):
                    intent = msg["intent"]
                else:
                    intent, _ = router.nlp.classify_intent(user_query)
                    
                msg["intent"] = intent
                is_visual = intent == "ANALYTICS"
                
                if is_visual or intent == "SEARCH":
                    try:
                        router_res = router.dispatch_query(user_query, user_id=user_id)
                        res_type = router_res["type"]
                        msg["is_visual"] = res_type in ("table_only", "table_stream")
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
                        msg["chart_data"] = router_res.get("chart_data")
                        msg["citations"] = router_res.get("citations")
                        msg["threshold_used"] = router_res.get("threshold_used")
                        msg["row_count"] = router_res.get("row_count")
                        msg["score_range"] = router_res.get("score_range")
                        msg["scores_list"] = router_res.get("scores_list")
                        print(f"PRE-POPULATED: query='{user_query}' | res_type='{res_type}' | chart_type='{msg['chart_type']}' | df_len={len(msg['df']) if msg['df'] is not None else 0}")
                        
                        # Cache the result if it was a cache miss (i.e. executed dynamically during prepopulation)
                        if "generated_response" not in router_res:
                            router_res["generated_response"] = msg["content"]
                            if res_type == "table_stream" and "messages" in router_res["data"]:
                                # Replace generator with the final generated string so it can be JSON serialized
                                router_res["data"]["messages"] = msg["content"]
                            router.cache.set(user_query, user_id, router_res)
                    except Exception as e:
                        print(f"Error pre-populating history item: {e}")
            if "is_visual" not in msg:
                msg["is_visual"] = False
    return history

def render_plotly_chart(chart_type, df, title, key=None):
    """Renders the appropriate Plotly figure based on the selector type."""
    if df.empty:
        return
        
    # Copy dataframe to prevent mutating original data
    df = df.copy()
    
    # Drop duplicate rows
    df = df.drop_duplicates()
    
    # Drop rows that have proper NaN/None values
    df = df.dropna()
    
    import pandas.api.types as ptypes
    
    # Also drop rows where any column contains literal "nan", "none", "null", "0", 0, or empty strings
    for col in df.columns:
        if ptypes.is_numeric_dtype(df[col]):
            df = df[df[col] != 0]
        else:
            mask = df[col].astype(str).str.strip().str.lower().isin(['', 'nan', 'none', 'null', 'na', '0'])
            df = df[~mask]
            
    if df.empty:
        return
    
    # If the dataframe has only 1 column and it is non-numeric, convert it to a frequency count so we can plot it
    if len(df.columns) == 1 and not ptypes.is_numeric_dtype(df[df.columns[0]]):
        col_name = df.columns[0]
        df = df[col_name].value_counts().reset_index()
        df.columns = [col_name, "count"]
        
    # If this is an unaggregated RAG search result, aggregate it by causal_parts_name
    elif 'similarity' in df.columns and 'causal_parts_name' in df.columns:
        df = df['causal_parts_name'].value_counts().reset_index()
        df.columns = ['causal_parts_name', 'count']
        
    # Ensure numeric columns are properly cast and clean up non-numeric columns for y-axes
    x_col = "period" if "period" in df.columns else df.columns[0]
    for c in df.columns:
        if c not in [x_col, "report_year", "report_month"]:
            try:
                df[c] = pd.to_numeric(df[c])
            except Exception:
                pass
                
    fig = None
    if chart_type == "horizontal_bar":
        # Ensure numeric value column
        val_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_horizontal_bar(df, val_col, df.columns[0], title)
    elif chart_type == "line":
        y_cols = [c for c in df.columns if c not in [x_col, "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        if not y_cols and len(df.columns) > 1:
            try:
                df[df.columns[1]] = pd.to_numeric(df[df.columns[1]], errors='coerce')
                y_cols = [df.columns[1]]
            except:
                pass
        fig = plot_line_trend(df, x_col, y_cols, title)
    elif chart_type == "donut":
        val_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_donut_chart(df, df.columns[0], val_col, title)
    elif chart_type == "histogram":
        val_col = df.columns[0]
        try:
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        except:
            pass
        fig = plot_histogram(df, val_col, title)
    elif chart_type == "radar":
        y_cols = [c for c in df.columns if c not in [df.columns[0], "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_radar_comparison(df, df.columns[0], list(y_cols[:3]), title)
    elif chart_type == "grouped_bar":
        y_cols = [c for c in df.columns if c not in [df.columns[0], "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_grouped_bar(df, df.columns[0], list(y_cols), title)
    elif chart_type == "scatter":
        x_val = df.columns[0]
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[x_val] = pd.to_numeric(df[x_val], errors='coerce')
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_scatter_plot(df, x_val, y_val, title)
    elif chart_type == "box":
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_box_plot(df, df.columns[0], y_val, title)
    elif chart_type == "violin":
        y_val = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        try:
            df[y_val] = pd.to_numeric(df[y_val], errors='coerce')
        except:
            pass
        fig = plot_violin_plot(df, df.columns[0], y_val, title)
    elif chart_type == "area":
        y_cols = [c for c in df.columns if c not in [x_col, "report_year", "report_month"] and ptypes.is_numeric_dtype(df[c])]
        fig = plot_area_chart(df, x_col, list(y_cols), title)
        
    if fig:
        st.plotly_chart(fig, width="stretch", key=key)

def render_dashboard_page(router):
    """Renders the comprehensive quality stats dashboard page."""
    ae = router.analytics_engine

    # ─── Header ──────────────────────────────────────────────────────────────
    st.markdown("""
        <div style="margin-bottom:1.25rem; padding-bottom:1rem; border-bottom:1px solid #e2e8f0;">
            <div style="font-size:1.5rem;font-weight:700;color:#0f172a;letter-spacing:-0.02em;">
                📊 Quality Analytics Dashboard
            </div>
            <div style="font-size:0.875rem;color:#64748b;margin-top:4px;">
                Pre-aggregated metrics from SQLite materialized view tables — filtered in real time.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # ─── Interactive Filters ──────────────────────────────────────────────────
    st.markdown("<div class='section-label'>Dashboard Filters</div>", unsafe_allow_html=True)
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 1])

    @st.cache_data(ttl=300)
    def _get_dashboard_filter_options(_ae):
        """Cached lookup of distinct filter values — refreshes every 5 minutes."""
        return (
            _ae.get_distinct_years(),
            _ae.get_distinct_models(),
            _ae.get_distinct_countries(),
        )

    all_years, all_models, all_countries = _get_dashboard_filter_options(ae)

    def reset_filters_callback():
        st.session_state.dash_year = "All Years"
        st.session_state.dash_model = "All Models"
        st.session_state.dash_country = "All Countries"

    with f_col1:
        year_opts = ["All Years"] + [str(y) for y in all_years]
        sel_year  = st.selectbox("Report Year", year_opts, key="dash_year")
    with f_col2:
        model_opts = ["All Models"] + all_models
        sel_model  = st.selectbox("Product Model", model_opts, key="dash_model")
    with f_col3:
        country_opts = ["All Countries"] + all_countries
        sel_country  = st.selectbox("Outbreak Country", country_opts, key="dash_country")
    with f_col4:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.button("Reset Filters", type="secondary", width="stretch", on_click=reset_filters_callback)

    flt_year    = int(sel_year)    if sel_year    != "All Years"    else None
    flt_model   = sel_model        if sel_model   != "All Models"   else None
    flt_country = sel_country      if sel_country != "All Countries" else None

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    # ─── Build WHERE clause for raw KPI queries ───────────────────────────────
    kpi_clauses = []
    kpi_params  = []
    if flt_year:
        kpi_clauses.append("report_year = ?")
        kpi_params.append(flt_year)
    if flt_model:
        kpi_clauses.append("product_model_code = ?")
        kpi_params.append(flt_model)
    if flt_country:
        kpi_clauses.append("outbreak_country = ?")
        kpi_params.append(flt_country)
    where_kpi = f"WHERE {' AND '.join(kpi_clauses)}" if kpi_clauses else ""

    from core.database import get_engine
    conn   = get_engine(router.db_path).raw_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) FROM records {where_kpi};", kpi_params)
    total_records = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT product_model_code) FROM records {where_kpi};", kpi_params)
    total_models = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT reported_company) FROM records {where_kpi};", kpi_params)
    total_dealers = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM records {where_kpi} {'AND' if where_kpi else 'WHERE'} is_resolved = 1;", kpi_params)
    resolved_claims = cursor.fetchone()[0]

    unresolved_claims = total_records - resolved_claims
    resolution_pct    = (resolved_claims * 100 / total_records) if total_records > 0 else 0

    avg_mileage_resolved = ae.get_avg_resolution_mileage(year=flt_year, model=flt_model, country=flt_country)

    cursor.execute(f"SELECT COUNT(DISTINCT outbreak_country) FROM records {where_kpi};", kpi_params)
    total_countries = cursor.fetchone()[0]

    conn.close()

    # ─── 6 KPI Cards ─────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    kpi_cards = [
        (k1, "metric-card-blue",    "Total FTIR Records",      f"{total_records:,}",                         ""),
        (k2, "metric-card-teal",    "Product Models",          f"{total_models}",                            ""),
        (k3, "metric-card-amber",   "Active Dealers",          f"{total_dealers}",                           ""),
        (k4, "metric-card-emerald", "Resolved Claims",         f"{resolved_claims:,}",                       f"<span style='font-size:12px;color:#059669;'>({resolution_pct:.1f}%)</span>"),
        (k5, "metric-card",         "Unresolved Claims",       f"<span style='color:#ef4444;'>{unresolved_claims:,}</span>", ""),
        (k6, "metric-card",         "Avg Resolution Mileage",  f"{avg_mileage_resolved:,} <span style='font-size:12px;color:#64748b;'>km</span>", ""),
    ]
    for col, card_cls, label, value, extra in kpi_cards:
        with col:
            st.markdown(
                f"<div class='metric-card {card_cls}'>"
                f"<div class='metric-label'>{label}</div>"
                f"<div class='metric-value'>{value} {extra}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    # ─── Row 1: Trouble Codes + Monthly Trend ────────────────────────────────
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        df_tc, _ = ae.get_trouble_code_frequency(limit=10, model=flt_model, year=flt_year, country=flt_country)
        if not df_tc.empty:
            fig_tc = plot_horizontal_bar(df_tc, 'count', 'trouble_code', "Top 10 Trouble Codes by Claims")
            st.plotly_chart(fig_tc, width="stretch", key="dash_tc")
        else:
            st.info("No trouble code data for the current filters.")

    with r1c2:
        df_trend, _ = ae.get_monthly_failure_trend(year=flt_year, model=flt_model, country=flt_country)
        if not df_trend.empty:
            fig_trend = plot_line_trend(df_trend, 'period', 'failures', "Monthly Claims Trend")
            st.plotly_chart(fig_trend, width="stretch", key="dash_trend")
        else:
            st.info("No trend data for the current filters.")

    # ─── Row 2: Quality Distribution + Top Countries ─────────────────────────
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        df_qual, _ = ae.get_quality_distribution(model=flt_model, year=flt_year, country=flt_country)
        if not df_qual.empty:
            fig_qual = plot_donut_chart(df_qual, 'quality', 'count', "Quality Ratings Distribution")
            st.plotly_chart(fig_qual, width="stretch", key="dash_qual")
        else:
            st.info("No quality data for the current filters.")

    with r2c2:
        df_cntry, _ = ae.get_top_dealers_or_countries(by="country", limit=10, year=flt_year, model=flt_model)
        if not df_cntry.empty:
            fig_cntry = plot_horizontal_bar(df_cntry, 'failures', 'country', "Top 10 Outbreak Countries")
            st.plotly_chart(fig_cntry, width="stretch", key="dash_cntry")
        else:
            st.info("No country data for the current filters.")

    # ─── Row 3: Failed Parts + Model Comparison (Plotly Grouped Bar) ─────────
    r3c1, r3c2 = st.columns(2)
    with r3c1:
        df_parts, _ = ae.get_failed_parts_frequency(limit=10, model=flt_model, year=flt_year, country=flt_country)
        if not df_parts.empty:
            fig_parts = plot_horizontal_bar(df_parts, 'count', 'part_name', "Top 10 Failed Parts")
            st.plotly_chart(fig_parts, width="stretch", key="dash_parts")
        else:
            st.info("No failed parts data for the current filters.")

    with r3c2:
        df_comp, _ = ae.get_model_comparison(year=flt_year, country=flt_country)
        if not df_comp.empty:
            df_comp_top = df_comp.head(10)
            fig_comp = plot_grouped_bar(
                df_comp_top,
                'model',
                ['total_claims', 'poor_quality_count'],
                "Model Performance: Total Claims vs Poor Quality"
            )
            st.plotly_chart(fig_comp, width="stretch", key="dash_comp")
        else:
            st.info("No model comparison data available.")

    # ─── Resolution Rate Progress Panel ──────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown("<div class='section-label'>Repair Resolution Rate by Trouble Code</div>", unsafe_allow_html=True)

    df_res, _ = ae.get_repair_success_rate(year=flt_year, model=flt_model, country=flt_country)
    if not df_res.empty:
        df_res_top = df_res.head(12)

        rows_html = ""
        for _, row in df_res_top.iterrows():
            tc        = str(row['trouble_code'])[:30]
            total     = int(row['total_cases'])
            rate      = float(row['success_rate'])
            bar_color = "#10b981" if rate >= 70 else ("#f59e0b" if rate >= 40 else "#ef4444")
            rows_html += f"""
            <tr>
                <td style="padding:8px 12px;font-size:12px;font-weight:600;color:#0f172a;width:35%;">{tc}</td>
                <td style="padding:8px 4px;font-size:11px;color:#64748b;text-align:center;width:10%;">{total}</td>
                <td style="padding:8px 12px;width:45%;">
                    <div style="background:#f1f5f9;border-radius:999px;height:10px;overflow:hidden;">
                        <div style="width:{rate}%;height:100%;background:{bar_color};border-radius:999px;transition:width 0.4s ease;"></div>
                    </div>
                </td>
                <td style="padding:8px 8px;font-size:12px;font-weight:700;color:{bar_color};text-align:right;width:10%;">{rate:.1f}%</td>
            </tr>"""

        st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;margin-bottom:1rem;">
                <table style="width:100%;border-collapse:collapse;">
                    <thead>
                        <tr style="background:#f8fafc;border-bottom:1px solid #e2e8f0;">
                            <th style="padding:10px 12px;font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Trouble Code</th>
                            <th style="padding:10px 4px;font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;text-align:center;">Cases</th>
                            <th style="padding:10px 12px;font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;text-align:left;">Resolution Rate</th>
                            <th style="padding:10px 8px;font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;text-align:right;">%</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("No resolution rate data available (minimum 5 cases required per trouble code).")

    # ─── Footer ───────────────────────────────────────────────────────────────
    from core.database import get_engine
    conn2  = get_engine(router.db_path).raw_connection()
    cur2   = conn2.cursor()
    cur2.execute("SELECT MAX(created_at) FROM records;")
    last_ts = cur2.fetchone()[0] or "N/A"
    conn2.close()
    filter_desc = " | ".join(filter(None, [
        f"Year: {flt_year}"    if flt_year    else None,
        f"Model: {flt_model}"  if flt_model   else None,
        f"Country: {flt_country}" if flt_country else None,
    ])) or "No filters applied"
    st.caption(f"🕒 Last record ingested: `{last_ts}` · Total records in view: `{total_records:,}` · Filters: {filter_desc}")

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
    logger.info("Application Started")
    try:
        main()
    except Exception as e:
        logger.exception("Top-level application error")
        st.error(f"An unexpected error occurred: {e}")
