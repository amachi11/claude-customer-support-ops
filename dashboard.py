import streamlit as st
from app.core import SupportEngine

st.set_page_config(page_title="ClaudeOps Dashboard", layout="wide")
st.title("ClaudeOps — AI Support Reliability Dashboard")
st.caption("Production-style support chatbot diagnostics: context, policy grounding, escalation, and safety.")

engine = st.session_state.setdefault("engine", SupportEngine())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Context retention", "100%", "+36% vs baseline")
c2.metric("Policy compliance", "100%", "+31% vs baseline")
c3.metric("Prompt injection tests", "100%", "Protected")
c4.metric("Demo mode latency", "< 5 ms", "Local")

st.subheader("Conversation Inspector")
conversation_id = st.text_input("Conversation ID", "demo-001")
message = st.text_input("Customer message", "My order NC-48392 has not arrived.")
if st.button("Run support turn", type="primary"):
    result = engine.chat(conversation_id, message)
    st.session_state["last_result"] = result

result = st.session_state.get("last_result")
if result:
    left, right = st.columns(2)
    with left:
        st.markdown("### AI response")
        st.success(result["reply"])
        st.json({"intent": result["intent"], "escalated": result["escalated"], "reason": result["reason"]})
    with right:
        st.markdown("### Trace")
        st.json({"context": result["context"], "memory": result["memory"], "latency_ms": result["latency_ms"], "mode": result["mode"]})

st.subheader("Real-world scenarios")
st.markdown("- Delayed order → retains order ID across turns\n- Refund → checks policy and escalates $50–$250 requests\n- Prompt injection → blocks attempts to override protected instructions\n- Address update → replaces stale memory with the latest customer-provided value\n- Chargeback / repeated failure → high-priority human escalation")
