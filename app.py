import streamlit as st
import time
import os
from dotenv import load_dotenv
from src.agents.agents import build_search_agent, build_reader_agent, writer_chain, critic_chain

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="LangChain Multi-Agent Research Assistant",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    
    if openrouter_key:
        st.success("✅ OpenRouter API Key configured")
    else:
        st.error("❌ OpenRouter API Key missing")
        
    if tavily_key:
        st.success("✅ Tavily API Key configured")
    else:
        st.error("❌ Tavily API Key missing")

    st.markdown("---")
    st.subheader("🤖 Multi-Agent Workflow")
    st.markdown("""
    1. **🔍 Search Agent**: Queries Tavily for real-time web results.
    2. **📄 Reader Agent**: Scrapes and extracts full text from top resources.
    3. **✍️ Writer Chain**: Synthesizes and structures the final research report.
    4. **🧐 Critic Chain**: Evaluates the report and provides critique.
    """)
    
    st.markdown("---")
    st.subheader("💡 Example Topics")
    example_topics = [
        "The impact of AI on the job market in 2026",
        "Future of LLMs and Agentic AI Architecture",
        "Breakthroughs in Quantum Computing in 2025-2026",
        "Autonomous Vehicles: Safety, Regulations, and Future",
    ]
    for ex in example_topics:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["topic_input"] = ex

# Main Title & Subtitle
st.title("🔬 Multi-Agent Research Assistant")
st.caption("Autonomous research powered by LangChain, OpenRouter, and Tavily.")

# Initialize session state
if "results" not in st.session_state:
    st.session_state["results"] = {}
if "topic_input" not in st.session_state:
    st.session_state["topic_input"] = ""

# Input Form
with st.form("research_form"):
    topic = st.text_input(
        "Enter your research topic:",
        value=st.session_state.get("topic_input", ""),
        placeholder="e.g., The impact of AI on the job market in 2026",
    )
    col1, col2 = st.columns([1, 5])
    with col1:
        submit_btn = st.form_submit_button("🚀 Start Research", type="primary", use_container_width=True)
    with col2:
        clear_btn = st.form_submit_button("🔄 Clear", use_container_width=False)

if clear_btn:
    st.session_state["results"] = {}
    st.session_state["topic_input"] = ""
    st.rerun()

# Execution Logic
if submit_btn:
    if not topic.strip():
        st.warning("Please enter a research topic to begin.")
    else:
        st.session_state["topic_input"] = topic
        st.session_state["results"] = {}
        
        with st.status("Executing Multi-Agent Research Pipeline...", expanded=True) as status:
            try:
                # Step 1: Search Agent
                st.write("🔍 **Step 1:** Search Agent is querying the web...")
                search_agent = build_search_agent()
                search_res = search_agent.invoke({
                    "messages": [("user", f"Find recent, reliable and detailed information about: {topic}")]
                })
                search_output = search_res["messages"][-1].content
                st.session_state["results"]["search"] = search_output
                st.write("✅ Search Agent completed.")

                # Step 2: Reader Agent
                st.write("📄 **Step 2:** Reader Agent is scraping deep content...")
                reader_agent = build_reader_agent()
                reader_res = reader_agent.invoke({
                    "messages": [(
                        "user",
                        f"Based on the following search results about '{topic}', "
                        f"pick the most relevant URL and scrape it for deeper content.\n\n"
                        f"Search Results:\n{search_output[:800]}"
                    )]
                })
                reader_output = reader_res["messages"][-1].content
                st.session_state["results"]["reader"] = reader_output
                st.write("✅ Reader Agent completed.")

                # Step 3: Writer Chain
                st.write("✍️ **Step 3:** Writer Chain is drafting the comprehensive report...")
                research_combined = (
                    f"SEARCH RESULTS:\n{search_output}\n\n"
                    f"DETAILED SCRAPED CONTENT:\n{reader_output}"
                )
                report_output = writer_chain.invoke({
                    "topic": topic,
                    "research": research_combined
                })
                st.session_state["results"]["report"] = report_output
                st.write("✅ Writer Chain completed.")

                # Step 4: Critic Chain
                st.write("🧐 **Step 4:** Critic Chain is evaluating the report...")
                critic_output = critic_chain.invoke({
                    "report": report_output
                })
                st.session_state["results"]["critic"] = critic_output
                st.write("✅ Critic Chain completed.")

                status.update(label="🎉 Research Pipeline Finished Successfully!", state="complete", expanded=False)

            except Exception as e:
                status.update(label="❌ An error occurred during research", state="error", expanded=True)
                st.error(f"Error details: {str(e)}")

# Display Results
res = st.session_state.get("results", {})
if res and "report" in res:
    st.markdown("---")
    st.subheader(f"📊 Research Dossier: {st.session_state.get('topic_input', '')}")
    
    tab_report, tab_critic, tab_sources, tab_reader = st.tabs([
        "📝 Final Report",
        "🧐 Critic Review",
        "🔍 Search Results",
        "📄 Scraped Content",
    ])
    
    with tab_report:
        st.markdown(res["report"])
        st.download_button(
            label="📥 Download Report as Markdown",
            data=res["report"],
            file_name=f"research_report_{int(time.time())}.md",
            mime="text/markdown",
            type="secondary",
        )
        
    with tab_critic:
        st.info("The Critic Agent evaluates the clarity, depth, source attribution, and objectivity of the report.")
        st.markdown(res.get("critic", "No critique available."))
        
    with tab_sources:
        st.markdown("### Raw Web Search Agent Output")
        st.text_area("Search Results", res.get("search", ""), height=300)
        
    with tab_reader:
        st.markdown("### Deep Scraped Content")
        st.text_area("Scraped Content", res.get("reader", ""), height=300)