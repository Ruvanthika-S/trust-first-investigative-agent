import streamlit as st

from agent import follow_up, run_agent

st.set_page_config(page_title="Trust-first investigative agent", layout="wide")

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
    }
    .stApp {
        background: linear-gradient(135deg, #07111f 0%, #111827 45%, #1f2937 100%);
    }
    [data-testid="stSidebar"] {
        background: rgba(2, 6, 23, 0.95);
        border-right: 1px solid rgba(255,255,255,0.08);
    }
    .hero-card {
        padding: 1.2rem 1.3rem;
        border-radius: 18px;
        border: 1px solid rgba(255,255,255,0.12);
        background: linear-gradient(90deg, rgba(124, 58, 237, 0.25), rgba(236, 72, 153, 0.16));
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        margin-bottom: 1rem;
    }
    .hero-title {
        font-size: 1.7rem;
        font-weight: 800;
        color: #f8fafc;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #e2e8f0;
        margin-top: 0.25rem;
    }
    .panel {
        padding: 1rem 1.1rem;
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.1);
        background: rgba(15, 23, 42, 0.7);
        margin-bottom: 1rem;
        box-shadow: 0 8px 24px rgba(0,0,0,0.18);
    }
    .pill {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        background: rgba(124, 58, 237, 0.25);
        color: #f5f3ff;
        font-size: 0.8rem;
        font-weight: 700;
        margin-bottom: 0.4rem;
    }
    .stButton > button {
        background: linear-gradient(90deg, #7C3AED, #EC4899);
        color: white;
        border: none;
        border-radius: 999px;
        font-weight: 700;
        padding: 0.45rem 1rem;
        box-shadow: 0 6px 20px rgba(236, 72, 153, 0.22);
    }
    .stButton > button:hover {
        filter: brightness(1.08);
    }
    div[data-testid="stExpander"] {
        border-radius: 12px;
        border: 1px solid rgba(124, 58, 237, 0.35);
        background: rgba(15, 23, 42, 0.6);
        margin-bottom: 0.5rem;
    }
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 1px solid rgba(124, 58, 237, 0.6);
        background: rgba(15, 23, 42, 0.9);
        color: #f8fafc;
    }
    .stAlert, .stSuccess, .stError, .stInfo {
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title"> Trust-first investigative agent</div>
        <div class="hero-subtitle">Break down a claim, gather evidence, and inspect the reasoning step by step.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.session_state.setdefault("last_result", None)
st.session_state.setdefault("history", [])
st.session_state.setdefault("question_input", "")
st.session_state.setdefault("follow_up_chats", {})
st.session_state.setdefault("active_chat_key", None)
st.session_state.setdefault("clear_input", False)

if st.session_state.get("clear_input"):
    st.session_state.clear_input = False
    st.session_state.question_input = ""

with st.sidebar:
    st.header("How it works?")
    st.write("The assistant will:")
    st.markdown("- break your question into smaller checkable claims")
    st.markdown("- search for likely sources")
    st.markdown("- summarize the evidence and rank the sources")
    st.divider()
    st.subheader("Try one!!")
    example_prompts = [
        "Is it true that coffee stunts your growth?",
        "Does drinking water every 20 minutes help your metabolism?",
        "Is the moon landing fake?",
    ]
    for example in example_prompts:
        if st.button(example, key=f"example_{example}"):
            st.session_state.question_input = example
    st.divider()
    st.subheader("History")
    if st.session_state.history:
        for i, item in enumerate(reversed(st.session_state.history[-8:])):
            if st.button(item["question"], key=f"history_{i}_{item['question']}"):
                st.session_state.last_result = item["result"]
                st.session_state.active_chat_key = item["question"]
                st.session_state.question_input = item["question"]
                st.rerun()
    else:
        st.caption("No investigations yet")

st.markdown('<div class="panel">', unsafe_allow_html=True)
col1, col2 = st.columns([3.6, 1.2])
with col2:
    clear_clicked = st.button("Clear", use_container_width=True)
    investigate_clicked = st.button("Investigate", use_container_width=True)
with col1:
    question = st.text_input("Ask something you want fact-checked:", key="question_input")

if clear_clicked:
    st.session_state.clear_input = True
    st.session_state.last_result = None
    st.session_state.active_chat_key = None
    st.session_state.follow_up_chats.pop(st.session_state.get("active_chat_key"), None)
    st.rerun()

if investigate_clicked and question:
    with st.spinner("Investigating..."):
        result = run_agent(question)
        st.session_state.last_result = result
        st.session_state.active_chat_key = question
        st.session_state.follow_up_chats.setdefault(question, [])
        st.session_state.history.append({"question": question, "result": result, "follow_up_chat": []})
st.markdown('</div>', unsafe_allow_html=True)

if not question:
    st.markdown('<div class="panel"><span class="pill">Ready to investigate</span><br>Enter a claim or select one of the examples to start a fact-check.</div>', unsafe_allow_html=True)

if st.session_state.last_result is not None:
    result = st.session_state.last_result
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("🧾 Final answer")
    if result.get("confidence") == "high":
        st.success(result["answer"])
    elif result.get("confidence") == "low":
        st.error(result["answer"])
    else:
        st.info(result["answer"])

    st.caption(f"Estimated confidence: {result.get('confidence', 'medium')}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Ask a follow-up")
    st.write("Open a dedicated follow-up workspace for this investigation.")
    if st.button("Open follow-up page", use_container_width=True):
        st.session_state.active_chat_key = question
        st.switch_page("pages/follow_up.py")
    st.markdown('</div>', unsafe_allow_html=True)

    evidence_summary = result.get("evidence_summary") or {}
    if evidence_summary:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Evidence summary")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Claims checked", evidence_summary.get("claim_count", 0))
        col_b.metric("Supporting evidence", evidence_summary.get("overall_support", 0))
        col_c.metric("Contradicting evidence", evidence_summary.get("overall_contradict", 0))
        col_d.metric("Irrelevant evidence", evidence_summary.get("overall_irrelevant", 0))

        for item in evidence_summary.get("evidence_by_claim", []):
            st.write(f"- {item['claim']}: support={item['support']}, contradict={item['contradict']}, irrelevant={item['irrelevant']}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Reasoning trace")
    for step in result.get("trace", []):
        detail = step.get("detail", "")
        if step.get("step") == "summary":
            continue
        with st.expander(f"{step['step'].upper()}: {detail[:70]}{'...' if len(detail) > 70 else ''}"):
            st.write(detail)
            if "sources" in step:
                for source in step["sources"]:
                    title = source.get("title", "Untitled")
                    url = source.get("url", "#")
                    st.markdown(f"- [{title}]({url})")
            if step.get("source_url"):
                st.markdown(f"[Open source]({step['source_url']})")
            if step.get("credibility"):
                credibility = step["credibility"]
                st.caption(f"Credibility: {credibility['label']} ({credibility['score']})")
    st.markdown('</div>', unsafe_allow_html=True)