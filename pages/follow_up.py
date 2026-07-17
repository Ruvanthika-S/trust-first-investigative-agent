import streamlit as st

from agent import follow_up

st.set_page_config(page_title="Follow-up chat", layout="centered")

if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "follow_up_chats" not in st.session_state:
    st.session_state.follow_up_chats = {}
if "active_chat_key" not in st.session_state:
    st.session_state.active_chat_key = None
if "history" not in st.session_state:
    st.session_state.history = []

if st.session_state.last_result is None:
    st.info("Open an investigation first from the main page to start a follow-up thread.")
    st.stop()

result = st.session_state.last_result
question = st.session_state.get("active_chat_key") or st.session_state.get("question_input", "")
chat_key = question or "current-investigation"

match = next((item for item in st.session_state.history if item.get("question") == question), None)
if match is not None:
    chat_history = match.get("follow_up_chat", [])
else:
    chat_history = st.session_state.follow_up_chats.get(chat_key, [])

st.title("💬 Follow-up chat")
st.caption(f"Conversation for: {question}")

for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

follow_up_msg = st.chat_input("Ask something about this investigation...")
if follow_up_msg:
    chat_history.append({"role": "user", "content": follow_up_msg})
    st.session_state.follow_up_chats[chat_key] = chat_history
    if match is not None:
        match["follow_up_chat"] = chat_history
    with st.spinner("Thinking..."):
        reply = follow_up(
            question,
            result["answer"],
            result.get("trace", []),
            follow_up_msg,
            chat_history,
        )
    chat_history.append({"role": "assistant", "content": reply})
    st.session_state.follow_up_chats[chat_key] = chat_history
    if match is not None:
        match["follow_up_chat"] = chat_history
    st.rerun()
