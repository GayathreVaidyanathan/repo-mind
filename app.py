import streamlit as st
import time
import json
from pathlib import Path

from ingestor import ingest, cleanup
from retriever import ask, get_sources
from analyzer import run_analysis, run_summaries
from graph import run_graph_analysis

# ---------------------------------------------------------------------------
# PAGE CONFIG — must be first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="RepoMind",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# GLOBAL CSS — professional dark theme
# ---------------------------------------------------------------------------

st.markdown("""
<style>
  /* ── Base ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
  }

  .stApp {
    background-color: #0d1117;
    color: #e6edf3;
  }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
  }
  [data-testid="stSidebar"] * { color: #e6edf3 !important; }

  /* ── Hide Streamlit branding ── */
  #MainMenu, footer, header { visibility: hidden; }

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {
    background-color: #161b22;
    border-bottom: 1px solid #21262d;
    gap: 0;
    padding: 0 1rem;
  }
  .stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #8b949e;
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    font-weight: 500;
    padding: 0.75rem 1.25rem;
    border-bottom: 2px solid transparent;
    border-radius: 0;
  }
  .stTabs [aria-selected="true"] {
    background-color: transparent !important;
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
  }
  .stTabs [data-baseweb="tab-panel"] {
    background-color: #0d1117;
    padding-top: 1.5rem;
  }

  /* ── Inputs ── */
  .stTextInput input, .stTextArea textarea {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 6px !important;
    color: #e6edf3 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.875rem !important;
  }
  .stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #58a6ff !important;
    box-shadow: 0 0 0 3px rgba(88,166,255,0.1) !important;
  }

  /* ── Buttons ── */
  .stButton button {
    background-color: #238636 !important;
    color: #ffffff !important;
    border: 1px solid #2ea043 !important;
    border-radius: 6px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
  }
  .stButton button:hover {
    background-color: #2ea043 !important;
    border-color: #3fb950 !important;
    transform: translateY(-1px) !important;
  }

  /* ── Metric cards ── */
  [data-testid="stMetric"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
  }
  [data-testid="stMetricLabel"] { color: #8b949e !important; font-size: 0.78rem !important; text-transform: uppercase; letter-spacing: 0.08em; }
  [data-testid="stMetricValue"] { color: #e6edf3 !important; font-size: 1.8rem !important; font-weight: 600 !important; }

  /* ── Code blocks ── */
  code, .stCode {
    font-family: 'JetBrains Mono', monospace !important;
    background-color: #161b22 !important;
    border: 1px solid #21262d !important;
    border-radius: 6px !important;
    color: #79c0ff !important;
    font-size: 0.82rem !important;
  }

  /* ── Expanders ── */
  [data-testid="stExpander"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
  }
  [data-testid="stExpander"] summary { color: #e6edf3 !important; font-weight: 500; }

  /* ── Divider ── */
  hr { border-color: #21262d !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0d1117; }
  ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #484f58; }

  /* ── Custom components ── */
  .rm-header {
    padding: 1.5rem 0 1rem;
    border-bottom: 1px solid #21262d;
    margin-bottom: 1.5rem;
  }
  .rm-logo {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 500;
    color: #58a6ff;
    letter-spacing: -0.02em;
  }
  .rm-logo span { color: #3fb950; }
  .rm-tagline {
    font-size: 0.82rem;
    color: #8b949e;
    margin-top: 0.2rem;
    font-family: 'JetBrains Mono', monospace;
  }

  .badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 500;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    letter-spacing: 0.04em;
  }
  .badge-critical { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
  .badge-warning  { background: rgba(210,153,34,0.15);  color: #d2a20a; border: 1px solid rgba(210,153,34,0.3); }
  .badge-info     { background: rgba(88,166,255,0.12); color: #58a6ff; border: 1px solid rgba(88,166,255,0.25); }
  .badge-green    { background: rgba(63,185,80,0.12);  color: #3fb950; border: 1px solid rgba(63,185,80,0.25); }

  .issue-card {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    border-left: 3px solid #30363d;
  }
  .issue-card.critical { border-left-color: #f85149; }
  .issue-card.warning  { border-left-color: #d2a20a; }
  .issue-card.info     { border-left-color: #58a6ff; }

  .issue-title {
    font-weight: 600;
    font-size: 0.9rem;
    color: #e6edf3;
    margin-bottom: 0.4rem;
  }
  .issue-desc {
    font-size: 0.82rem;
    color: #8b949e;
    line-height: 1.6;
    margin-bottom: 0.5rem;
  }
  .issue-fix {
    font-size: 0.8rem;
    color: #3fb950;
    font-family: 'JetBrains Mono', monospace;
  }
  .issue-meta {
    font-size: 0.72rem;
    color: #484f58;
    font-family: 'JetBrains Mono', monospace;
    margin-top: 0.5rem;
  }

  .file-card {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
    transition: border-color 0.2s;
  }
  .file-card:hover { border-color: #30363d; }
  .file-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #79c0ff;
    font-weight: 500;
  }
  .file-meta {
    font-size: 0.75rem;
    color: #8b949e;
    margin-top: 0.3rem;
  }

  .chat-msg-user {
    background-color: #1c2128;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 0.875rem 1.1rem;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
    color: #e6edf3;
  }
  .chat-msg-ai {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 0.875rem 1.1rem;
    margin-bottom: 1.25rem;
    font-size: 0.875rem;
    color: #c9d1d9;
    line-height: 1.7;
  }
  .source-chip {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #8b949e;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 0.15rem 0.5rem;
    margin: 0.15rem;
  }

  .stat-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }
  .stat-box {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.5rem;
    min-width: 120px;
    text-align: center;
  }
  .stat-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 600;
    color: #e6edf3;
    line-height: 1;
  }
  .stat-label {
    font-size: 0.72rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.4rem;
  }

  .node-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.6rem;
  }
  .node-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.9rem;
    color: #79c0ff;
    font-weight: 500;
    margin-bottom: 0.4rem;
  }
  .node-meta { font-size: 0.78rem; color: #8b949e; }

  .section-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #8b949e;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #21262d;
  }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SESSION STATE INITIALISATION
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "collection":   None,
        "repo_path":    None,
        "files":        None,
        "repo_url":     "",
        "ingested":     False,
        "analysis":     None,
        "summaries":    None,
        "graph_stats":  None,
        "chat_history": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("""
    <div class="rm-header">
      <div class="rm-logo">repo<span>mind</span></div>
      <div class="rm-tagline">// AI-powered code intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-label">Repository</div>', unsafe_allow_html=True)

    repo_url = st.text_input(
        "GitHub URL",
        placeholder="https://github.com/user/repo",
        label_visibility="collapsed"
    )

    analyse_btn = st.button("⚡ Analyse Repository", use_container_width=True)

    if st.session_state.ingested:
        st.markdown("---")
        st.markdown('<div class="section-label">Status</div>', unsafe_allow_html=True)
        st.markdown(f'<span class="badge badge-green">● Connected</span>', unsafe_allow_html=True)

        files = st.session_state.files or []
        py_files = [f for f in files if f["extension"] == ".py"]
        st.markdown(f"""
        <div style="margin-top:0.75rem; font-size:0.78rem; color:#8b949e; line-height:2;">
            <span style="color:#e6edf3; font-family:'JetBrains Mono',monospace;">{len(files)}</span> files loaded<br>
            <span style="color:#e6edf3; font-family:'JetBrains Mono',monospace;">{len(py_files)}</span> Python files<br>
            <span style="color:#e6edf3; font-family:'JetBrains Mono',monospace;">{st.session_state.collection.count() if st.session_state.collection else 0}</span> chunks indexed
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Reset", use_container_width=True):
            if st.session_state.repo_path:
                try:
                    cleanup(st.session_state.repo_path)
                except:
                    pass
            for key in ["collection", "repo_path", "files", "ingested",
                        "analysis", "summaries", "graph_stats", "chat_history"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.session_state.ingested = False
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#484f58; font-family:'JetBrains Mono',monospace; line-height:1.8;">
        powered by<br>
        LLaMA 3.3 70B · Groq<br>
        ChromaDB · all-MiniLM-L6
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# INGEST TRIGGER
# ---------------------------------------------------------------------------

if analyse_btn and repo_url:
    if st.session_state.repo_path:
        try:
            cleanup(st.session_state.repo_path)
        except:
            pass

    with st.spinner(""):
        progress = st.progress(0, text="Cloning repository...")
        try:
            collection, repo_path, files = ingest(repo_url)
            progress.progress(100, text="✅ Repository indexed")
            st.session_state.collection   = collection
            st.session_state.repo_path    = repo_path
            st.session_state.files        = files
            st.session_state.repo_url     = repo_url
            st.session_state.ingested     = True
            st.session_state.analysis     = None
            st.session_state.summaries    = None
            st.session_state.graph_stats  = None
            st.session_state.chat_history = []
            time.sleep(0.5)
            progress.empty()
            st.rerun()
        except Exception as e:
            progress.empty()
            st.error(f"Failed to ingest repository: {e}")


# ---------------------------------------------------------------------------
# MAIN CONTENT
# ---------------------------------------------------------------------------

if not st.session_state.ingested:
    # ── Landing screen ──
    st.markdown("""
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;
                min-height:70vh; text-align:center; padding:2rem;">
      <div style="font-family:'JetBrains Mono',monospace; font-size:3rem; font-weight:500;
                  color:#58a6ff; letter-spacing:-0.03em; margin-bottom:0.5rem;">
        repo<span style="color:#3fb950;">mind</span>
      </div>
      <div style="font-size:1.1rem; color:#8b949e; margin-bottom:0.5rem; font-weight:300;">
        AI-powered code intelligence for any GitHub repository
      </div>
      <div style="font-family:'JetBrains Mono',monospace; font-size:0.78rem; color:#484f58; margin-bottom:3rem;">
        paste a repo url in the sidebar to get started
      </div>
      <div style="display:flex; gap:2rem; flex-wrap:wrap; justify-content:center; max-width:700px;">
        <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:1.25rem 1.5rem; text-align:left; min-width:160px;">
          <div style="font-size:1.4rem; margin-bottom:0.5rem;">💬</div>
          <div style="font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:0.3rem;">Chat with Code</div>
          <div style="font-size:0.78rem; color:#8b949e;">Ask anything about the codebase in plain English</div>
        </div>
        <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:1.25rem 1.5rem; text-align:left; min-width:160px;">
          <div style="font-size:1.4rem; margin-bottom:0.5rem;">🔍</div>
          <div style="font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:0.3rem;">Bug Detection</div>
          <div style="font-size:0.78rem; color:#8b949e;">AI scans for security issues and anti-patterns</div>
        </div>
        <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:1.25rem 1.5rem; text-align:left; min-width:160px;">
          <div style="font-size:1.4rem; margin-bottom:0.5rem;">🗺️</div>
          <div style="font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:0.3rem;">Architecture Map</div>
          <div style="font-size:0.78rem; color:#8b949e;">Visualise file dependencies and structure</div>
        </div>
        <div style="background:#161b22; border:1px solid #21262d; border-radius:8px; padding:1.25rem 1.5rem; text-align:left; min-width:160px;">
          <div style="font-size:1.4rem; margin-bottom:0.5rem;">📖</div>
          <div style="font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:0.3rem;">Auto README</div>
          <div style="font-size:0.78rem; color:#8b949e;">Generate professional docs from source code</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

else:
    # ── Repo header ──
    repo_name = st.session_state.repo_url.rstrip("/").split("/")[-1]
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:1rem; padding:0.75rem 0 1.25rem;
                border-bottom:1px solid #21262d; margin-bottom:1.5rem;">
      <div style="font-family:'JetBrains Mono',monospace; font-size:1.1rem; color:#e6edf3; font-weight:500;">
        {repo_name}
      </div>
      <span class="badge badge-green">indexed</span>
      <div style="font-family:'JetBrains Mono',monospace; font-size:0.75rem; color:#8b949e;">
        {st.session_state.repo_url}
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬  Chat", "🔍  Analysis", "🗺️  Architecture", "📄  Files", "📖  README"
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — CHAT
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        # Suggested questions shown only when chat is empty
        if not st.session_state.chat_history:
            st.markdown("""
            <div style="text-align:center; padding:2.5rem 0 1.5rem; color:#8b949e; font-size:0.85rem;">
              Start by asking anything about the codebase
            </div>
            <div style="display:flex; gap:0.5rem; flex-wrap:wrap; justify-content:center; margin-bottom:2rem;">
              <span style="background:#161b22; border:1px solid #21262d; border-radius:6px; padding:0.4rem 0.85rem;
                           font-size:0.78rem; color:#8b949e; font-family:'JetBrains Mono',monospace;">
                "How does email sending work?"</span>
              <span style="background:#161b22; border:1px solid #21262d; border-radius:6px; padding:0.4rem 0.85rem;
                           font-size:0.78rem; color:#8b949e; font-family:'JetBrains Mono',monospace;">
                "What are the main classes?"</span>
              <span style="background:#161b22; border:1px solid #21262d; border-radius:6px; padding:0.4rem 0.85rem;
                           font-size:0.78rem; color:#8b949e; font-family:'JetBrains Mono',monospace;">
                "Explain the scraper logic"</span>
            </div>
            """, unsafe_allow_html=True)

        # Chat history display
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-msg-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-msg-ai">{msg["content"]}</div>', unsafe_allow_html=True)
                if msg.get("sources"):
                    chips = " ".join([f'<span class="source-chip">{s["path"]}</span>' for s in msg["sources"]])
                    st.markdown(f'<div style="margin-bottom:1.25rem; font-size:0.72rem; color:#484f58;">Sources: {chips}</div>', unsafe_allow_html=True)

        # Input always at the bottom — key uses counter so it clears after submit
        st.markdown('<div style="margin-top:1.5rem; border-top:1px solid #21262d; padding-top:1.25rem;"></div>', unsafe_allow_html=True)
        st.markdown('<div class="section-label">New question</div>', unsafe_allow_html=True)

        # Use a pending question pattern — store submitted question in state,
        # clear the widget, then process on the next rerun
        if "pending_question" not in st.session_state:
            st.session_state.pending_question = ""
        if "input_counter" not in st.session_state:
            st.session_state.input_counter = 0

        col1, col2 = st.columns([5, 1])
        with col1:
            question = st.text_input(
                "question",
                value="",
                placeholder="Ask anything about this codebase...",
                label_visibility="collapsed",
                key=f"chat_input_{st.session_state.input_counter}"
            )
        with col2:
            ask_btn = st.button("Ask →", use_container_width=True)

        # When Ask is clicked: save question, increment counter (clears box), rerun
        if ask_btn and question.strip():
            st.session_state.pending_question = question.strip()
            st.session_state.input_counter += 1
            st.rerun()

        # On rerun: if there's a pending question, process it now (input is already cleared)
        if st.session_state.pending_question:
            q = st.session_state.pending_question
            st.session_state.pending_question = ""
            st.session_state.chat_history.append({"role": "user", "content": q})

            with st.spinner("Thinking..."):
                sources = get_sources(q, st.session_state.collection)
                answer  = ""
                for chunk in ask(q, st.session_state.collection, stream=True):
                    answer += chunk

            st.session_state.chat_history.append({
                "role":    "assistant",
                "content": answer,
                "sources": sources
            })
            st.rerun()

        if st.session_state.chat_history and st.button("🗑 Clear chat", key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.input_counter += 1
            st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — ANALYSIS
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        if st.session_state.analysis is None:
            st.markdown("""
            <div style="text-align:center; padding:2rem; color:#8b949e; font-size:0.9rem;">
              Click below to run AI-powered bug detection and security analysis.
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 Run Analysis", use_container_width=False):
                with st.spinner("Scanning codebase for issues..."):
                    st.session_state.analysis = run_analysis(st.session_state.files)
                st.rerun()

        else:
            analysis = st.session_state.analysis

            # Summary metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total Issues",    analysis["total_issues"])
            c2.metric("🔴 Critical",     analysis["critical_count"])
            c3.metric("🟡 Warnings",     analysis["warning_count"])
            c4.metric("🔵 Info",         analysis["info_count"])
            c5.metric("Files Scanned",   analysis["files_analysed"])

            st.markdown("---")

            # Filter controls
            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                sev_filter = st.selectbox(
                    "Filter by severity",
                    ["All", "critical", "warning", "info"],
                    key="sev_filter"
                )
            with col_f2:
                type_filter = st.selectbox(
                    "Filter by type",
                    ["All"] + list(analysis["by_type"].keys()),
                    key="type_filter"
                )

            st.markdown("---")

            # Issues list
            for result in analysis["results"]:
                if not result["issues"]:
                    continue

                filtered = [
                    i for i in result["issues"]
                    if (sev_filter  == "All" or i.get("severity") == sev_filter)
                    and (type_filter == "All" or i.get("type")     == type_filter)
                ]
                if not filtered:
                    continue

                with st.expander(f"📄 `{result['path']}` — {len(filtered)} issue(s)"):
                    for issue in filtered:
                        sev  = issue.get("severity", "info")
                        typ  = issue.get("type", "")
                        badge_class = f"badge-{sev}"
                        card_class  = sev

                        st.markdown(f"""
                        <div class="issue-card {card_class}">
                          <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.5rem;">
                            <span class="badge {badge_class}">{sev.upper()}</span>
                            <span class="badge badge-info">{typ}</span>
                            <span class="issue-meta" style="margin:0;">line {issue.get('line_hint','?')}</span>
                          </div>
                          <div class="issue-title">{issue.get('title','')}</div>
                          <div class="issue-desc">{issue.get('description','')}</div>
                          <div class="issue-fix">→ {issue.get('suggestion','')}</div>
                        </div>
                        """, unsafe_allow_html=True)

            if st.button("🔄 Re-run Analysis", key="rerun_analysis"):
                st.session_state.analysis = None
                st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — ARCHITECTURE
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        if st.session_state.graph_stats is None:
            with st.spinner("Mapping architecture..."):
                st.session_state.graph_stats = run_graph_analysis(st.session_state.files)
            st.rerun()

        stats = st.session_state.graph_stats
        graph = stats["graph"]

        # Top metrics
        c1, c2, c3 = st.columns(3)
        c1.metric("Python Files",   stats["total_files"])
        c2.metric("Dependencies",   stats["total_edges"])
        c3.metric("Standalone",     len(stats["standalone"]))

        st.markdown("---")

        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown('<div class="section-label">Core Files (most imported)</div>', unsafe_allow_html=True)
            for node in stats["most_imported"]:
                classes_str = ", ".join(node.get("classes", [])) or "—"
                st.markdown(f"""
                <div class="node-card">
                  <div class="node-name">{node['label']}.py</div>
                  <div class="node-meta">
                    Imported by <strong style="color:#e6edf3;">{node['in_degree']}</strong> files &nbsp;·&nbsp;
                    {node['size']} lines<br>
                    Classes: {classes_str}
                  </div>
                </div>
                """, unsafe_allow_html=True)

        with col_b:
            st.markdown('<div class="section-label">Complex Files (most dependencies)</div>', unsafe_allow_html=True)
            for node in stats["most_complex"]:
                funcs = len(node.get("functions", []))
                st.markdown(f"""
                <div class="node-card">
                  <div class="node-name">{node['label']}.py</div>
                  <div class="node-meta">
                    Imports <strong style="color:#e6edf3;">{node['out_degree']}</strong> files &nbsp;·&nbsp;
                    {node['size']} lines &nbsp;·&nbsp; {funcs} functions
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-label">Dependency Map</div>', unsafe_allow_html=True)

        # Build ASCII-style dependency table
        if graph["edges"]:
            edges_data = []
            for edge in graph["edges"]:
                src = Path(edge["source"]).stem
                tgt = Path(edge["target"]).stem
                edges_data.append({"From": src, "→": "imports", "To": tgt})

            st.dataframe(
                edges_data,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.markdown('<div style="color:#8b949e; font-size:0.85rem;">No internal dependencies detected.</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-label">All Files</div>', unsafe_allow_html=True)
        for node in sorted(graph["nodes"], key=lambda n: n["in_degree"], reverse=True):
            classes_str   = ", ".join(node.get("classes",   [])) or "none"
            functions_str = ", ".join(node.get("functions", [])[:5])
            if len(node.get("functions", [])) > 5:
                functions_str += f" +{len(node['functions'])-5} more"

            st.markdown(f"""
            <div class="node-card">
              <div style="display:flex; align-items:center; gap:0.75rem;">
                <div class="node-name">{node['label']}.py</div>
                <span class="badge badge-info">in: {node['in_degree']}</span>
                <span class="badge badge-warning">out: {node['out_degree']}</span>
                <span style="font-size:0.72rem; color:#484f58; font-family:'JetBrains Mono',monospace;">{node['size']} lines</span>
              </div>
              <div class="node-meta" style="margin-top:0.4rem;">
                Classes: {classes_str}<br>
                Functions: {functions_str or 'none'}
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — FILES
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        files = st.session_state.files or []

        # Group by extension
        by_ext = {}
        for f in files:
            ext = f["extension"] or "other"
            by_ext.setdefault(ext, []).append(f)

        # Stats row
        total_lines = sum(len(f["content"].split("\n")) for f in files)
        st.markdown(f"""
        <div class="stat-row">
          <div class="stat-box">
            <div class="stat-num">{len(files)}</div>
            <div class="stat-label">Files</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">{total_lines:,}</div>
            <div class="stat-label">Lines</div>
          </div>
          <div class="stat-box">
            <div class="stat-num">{len(by_ext)}</div>
            <div class="stat-label">Types</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Files grouped by type
        for ext, ext_files in sorted(by_ext.items()):
            st.markdown(f'<div class="section-label">{ext} files ({len(ext_files)})</div>', unsafe_allow_html=True)
            for f in sorted(ext_files, key=lambda x: x["path"]):
                lines = len(f["content"].split("\n"))
                size  = len(f["content"].encode("utf-8"))
                size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
                st.markdown(f"""
                <div class="file-card">
                  <div class="file-name">{f['path']}</div>
                  <div class="file-meta">{lines} lines &nbsp;·&nbsp; {size_str}</div>
                </div>
                """, unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 5 — README GENERATOR
    # ════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-label">Auto-generate a professional README</div>', unsafe_allow_html=True)

        if st.button("📖 Generate README", key="gen_readme"):
            with st.spinner("Analysing codebase and writing documentation..."):

                # Get file summaries
                if st.session_state.summaries is None:
                    st.session_state.summaries = run_summaries(st.session_state.files)

                summaries = st.session_state.summaries
                repo_name = st.session_state.repo_url.rstrip("/").split("/")[-1]
                files     = st.session_state.files or []

                # Build context for README prompt
                summary_text = "\n".join([f"- {s['path']}: {s['summary']}" for s in summaries])
                file_list    = "\n".join([f['path'] for f in files])

                from groq import Groq
                from dotenv import load_dotenv
                import os
                load_dotenv()
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))

                readme_prompt = f"""You are a technical documentation expert. 
Generate a professional, comprehensive README.md for a GitHub repository.

Repository name: {repo_name}
Repository URL: {st.session_state.repo_url}

File structure:
{file_list}

File summaries:
{summary_text}

Write a complete README.md with these sections:
# {repo_name}
- One-line description
- Badges row (use shield.io style placeholders)
## Overview
## Features  
## Architecture
## Installation
## Usage
## Configuration
## Project Structure
## Contributing
## License

Make it professional, clear, and developer-friendly. Use proper markdown formatting."""

                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": readme_prompt}],
                    max_tokens=2048,
                    temperature=0.3,
                    stream=False
                )

                readme = response.choices[0].message.content

                # Display
                col_preview, col_raw = st.columns(2)

                with col_preview:
                    st.markdown('<div class="section-label">Preview</div>', unsafe_allow_html=True)
                    st.markdown(readme)

                with col_raw:
                    st.markdown('<div class="section-label">Raw Markdown</div>', unsafe_allow_html=True)
                    st.code(readme, language="markdown")

                st.download_button(
                    label="⬇️ Download README.md",
                    data=readme,
                    file_name="README.md",
                    mime="text/markdown"
                )