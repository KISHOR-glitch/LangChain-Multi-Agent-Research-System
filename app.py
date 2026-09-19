# Optional but recommended: create .streamlit/config.toml with this content
# so native widgets match the dark theme:
#
# [theme]
# base = "dark"
# primaryColor = "#10a37f"
# backgroundColor = "#212121"
# secondaryBackgroundColor = "#171717"
# textColor = "#ececec"
#
# Requires Streamlit 1.39 or newer.

import os
import time
import uuid

import streamlit as st
from dotenv import load_dotenv

from src.agents.agents import (
    build_search_agent,
    build_reader_agent,
    writer_chain,
    critic_chain,
)

load_dotenv()

st.set_page_config(
    page_title="Research Assistant",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ============================================================
# THEME (ChatGPT-style dark)
# ============================================================
CSS = """
<style>
:root {
  --bg: #212121; --sidebar: #171717; --surface: #2f2f2f; --hover: #2a2a2a;
  --border: #3a3a3a; --text: #ececec; --muted: #9b9b9b; --accent: #10a37f;
}
.stApp { background: var(--bg); color: var(--text); }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], [data-testid="stDecoration"], footer { display: none !important; }
.block-container { max-width: 768px; padding-top: 2rem; padding-bottom: 8rem; }

/* Sidebar */
section[data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid #262626; }
section[data-testid="stSidebar"] .stButton > button {
  background: transparent; border: none; color: var(--text);
  justify-content: flex-start; text-align: left; border-radius: 10px;
  padding: 0.55rem 0.75rem; font-weight: 400; box-shadow: none;
}
section[data-testid="stSidebar"] .stButton > button:hover { background: var(--hover); }
section[data-testid="stSidebar"] .stButton > button p {
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
[class*="st-key-conv_active"] button { background: var(--surface) !important; }
.st-key-new_chat button { border: 1px solid var(--border) !important; }
.brand { font-size: 1.05rem; font-weight: 600; padding: 0.25rem 0.25rem 0.75rem; }
.sidebar-label { color: var(--muted); font-size: 0.8rem; font-weight: 500; padding: 1rem 0.5rem 0.35rem; }
.status-row { font-size: 0.85rem; color: var(--muted); padding: 0.15rem 0; display: flex; align-items: center; gap: 0.5rem; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.ok { background: var(--accent); }
.dot.bad { background: #ef4444; }

/* Hero */
.hero { text-align: center; padding: 18vh 0 2rem; }
.hero h1 { font-size: 2rem; font-weight: 600; margin: 0 0 0.5rem; }
.hero p { color: var(--muted); margin: 0; }
.stMain .stButton > button {
  background: transparent; border: 1px solid var(--border); color: var(--text);
  border-radius: 16px; padding: 0.8rem 1rem; text-align: left;
  justify-content: flex-start; min-height: 3.4rem; height: auto; font-weight: 400;
}
.stMain .stButton > button:hover { background: var(--hover); border-color: #4a4a4a; }

/* Chat messages */
[data-testid="stChatMessage"] { background: transparent; padding: 0.6rem 0; gap: 0.9rem; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { flex-direction: row-reverse; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageAvatarUser"] { display: none; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
  background: var(--surface); border-radius: 1.4rem; padding: 0.7rem 1.1rem;
  max-width: 80%; width: fit-content;
}
[data-testid="stChatMessageAvatarAssistant"] { background: var(--accent); color: white; }

/* Chat input */
[data-testid="stBottom"] > div { background: var(--bg); }
[data-testid="stChatInput"] { background: #303030; border: 1px solid var(--border); border-radius: 26px; }
[data-testid="stChatInput"] textarea { background: transparent; color: var(--text); }
[data-testid="stChatInput"] button { background: var(--text); color: #000; border-radius: 50%; }

/* Misc */
[data-testid="stExpander"], [data-testid="stStatus"] {
  border: 1px solid var(--border); border-radius: 12px; background: transparent;
}
.stDownloadButton > button {
  background: transparent; border: 1px solid var(--border); color: var(--text); border-radius: 10px;
}
.stDownloadButton > button:hover { background: var(--hover); border-color: #4a4a4a; }
hr { border-color: #2c2c2c; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ============================================================
# CONSTANTS
# ============================================================
DEFAULT_TITLE = "New research"
ASSISTANT_AVATAR = ":material/science:"
EXAMPLES = [
    "The impact of AI on the job market in 2026",
    "Future of LLMs and Agentic AI Architecture",
    "Breakthroughs in Quantum Computing in 2025-2026",
    "Autonomous Vehicles: Safety, Regulations, and Future",
]

# ============================================================
# STATE
# ============================================================
def new_chat():
    active = st.session_state.get("active_id")
    if (
        active
        and active in st.session_state.conversations
        and not st.session_state.conversations[active]["messages"]
    ):
        return
    cid = uuid.uuid4().hex[:8]
    st.session_state.conversations[cid] = {"title": DEFAULT_TITLE, "messages": []}
    st.session_state.order.insert(0, cid)
    st.session_state.active_id = cid


def select_chat(cid):
    st.session_state.active_id = cid


def delete_chat(cid):
    st.session_state.conversations.pop(cid, None)
    if cid in st.session_state.order:
        st.session_state.order.remove(cid)
    if st.session_state.get("active_id") == cid:
        st.session_state.pop("active_id", None)
        if st.session_state.order:
            st.session_state.active_id = st.session_state.order[0]
        else:
            new_chat()


if "conversations" not in st.session_state:
    st.session_state.conversations = {}
    st.session_state.order = []
if "active_id" not in st.session_state:
    new_chat()
st.session_state.setdefault("pending_topic", None)

# ============================================================
# PIPELINE
# ============================================================
def run_research_pipeline(topic, on_step=None):
    def notify(msg):
        if on_step:
            on_step(msg)

    notify("Searching the web...")
    search_agent = build_search_agent()
    search_res = search_agent.invoke(
        {"messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]}
    )
    search_output = search_res["messages"][-1].content
    notify("Found sources")

    notify("Reading the most relevant page...")
    reader_agent = build_reader_agent()
    reader_res = reader_agent.invoke({
        "messages": [(
            "user",
            f"Based on the following search results about '{topic}', "
            f"pick the most relevant URL and scrape it for deeper content.\n\n"
            f"Search Results:\n{search_output[:800]}",
        )]
    })
    reader_output = reader_res["messages"][-1].content
    notify("Extracted page content")

    notify("Writing the report...")
    research_combined = (
        f"SEARCH RESULTS:\n{search_output}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{reader_output}"
    )
    report_output = writer_chain.invoke({"topic": topic, "research": research_combined})
    notify("Report drafted")

    notify("Reviewing the report...")
    critic_output = critic_chain.invoke({"report": report_output})
    notify("Review complete")

    return {
        "search": search_output,
        "reader": reader_output,
        "report": report_output,
        "critic": critic_output,
    }

# ============================================================
# UI COMPONENTS
# ============================================================
def render_sidebar():
    with st.sidebar:
        st.markdown('<div class="brand">Research Assistant</div>', unsafe_allow_html=True)
        st.button(
            "New research",
            key="new_chat",
            icon=":material/add:",
            use_container_width=True,
            on_click=new_chat,
        )

        st.markdown('<div class="sidebar-label">Recent</div>', unsafe_allow_html=True)
        has_history = False
        for cid in list(st.session_state.order):
            chat = st.session_state.conversations[cid]
            if not chat["messages"]:
                continue
            has_history = True
            active = cid == st.session_state.active_id
            key = f"conv_active_{cid}" if active else f"conv_{cid}"
            c1, c2 = st.columns([5, 1])
            with c1:
                st.button(
                    chat["title"], key=key, use_container_width=True,
                    on_click=select_chat, args=(cid,),
                )
            with c2:
                st.button(
                    "", key=f"del_{cid}", icon=":material/close:",
                    on_click=delete_chat, args=(cid,),
                )
        if not has_history:
            st.markdown('<div class="status-row">No research yet</div>', unsafe_allow_html=True)

        st.divider()
        with st.expander("How it works"):
            st.markdown(
                "1. **Search agent** queries Tavily for live web results.\n"
                "2. **Reader agent** scrapes the best page.\n"
                "3. **Writer chain** drafts the report.\n"
                "4. **Critic chain** reviews it."
            )
        with st.expander("API status"):
            for label, env in (("OpenRouter", "OPENROUTER_API_KEY"), ("Tavily", "TAVILY_API_KEY")):
                ok = bool(os.getenv(env))
                st.markdown(
                    f'<div class="status-row"><span class="dot {"ok" if ok else "bad"}"></span>'
                    f'{label} {"connected" if ok else "key missing"}</div>',
                    unsafe_allow_html=True,
                )


def render_hero():
    st.markdown(
        '<div class="hero"><h1>What do you want to research?</h1>'
        "<p>Ask about any topic. Four agents will search, read, write and review.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, ex in enumerate(EXAMPLES):
        with cols[i % 2]:
            if st.button(ex, key=f"ex_{i}", use_container_width=True):
                st.session_state.pending_topic = ex
                st.rerun()


def render_assistant_message(msg, key):
    if msg.get("error"):
        st.error(f"Something went wrong: {msg['error']}")
        return

    st.markdown(msg["report"])
    st.download_button(
        "Download report (.md)",
        data=msg["report"],
        file_name=f"research_report_{msg.get('ts', int(time.time()))}.md",
        mime="text/markdown",
        icon=":material/download:",
        key=f"dl_{key}",
    )
    with st.expander("Review and sources"):
        t_critic, t_search, t_reader = st.tabs(
            ["Critic review", "Search results", "Scraped content"]
        )
        with t_critic:
            st.markdown(msg.get("critic") or "No critique available.")
        with t_search:
            st.markdown(msg.get("search") or "")
        with t_reader:
            st.markdown(msg.get("reader") or "")

# ============================================================
# MAIN
# ============================================================
render_sidebar()
chat = st.session_state.conversations[st.session_state.active_id]

prompt = st.chat_input("Enter a research topic...")
topic = (prompt or st.session_state.pop("pending_topic", None) or "").strip()

if not chat["messages"] and not topic:
    render_hero()

for i, msg in enumerate(chat["messages"]):
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            render_assistant_message(msg, key=f"{st.session_state.active_id}_{i}")

if topic:
    chat["messages"].append({"role": "user", "content": topic})
    if chat["title"] == DEFAULT_TITLE:
        chat["title"] = topic[:40]

    with st.chat_message("user"):
        st.markdown(topic)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        with st.status("Researching...", expanded=True) as status:
            try:
                results = run_research_pipeline(topic, on_step=st.write)
                status.update(label="Research complete", state="complete", expanded=False)
                chat["messages"].append(
                    {"role": "assistant", "topic": topic, "ts": int(time.time()), **results}
                )
            except Exception as e:
                status.update(label="Research failed", state="error", expanded=True)
                chat["messages"].append({"role": "assistant", "error": str(e)})

    st.rerun()