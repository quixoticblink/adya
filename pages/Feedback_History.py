import streamlit as st
import json
import os
import datetime

st.set_page_config(page_title="Feedback History", page_icon="📜", layout="wide")

st.title("📜 Feedback History")
st.caption("View past answers and AI feedback.")

HISTORY_FILE = "feedback_history.json"

if not os.path.exists(HISTORY_FILE):
    st.info("No history found yet. completes some questions to see them here!")
    st.stop()

try:
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
        # Reverse to show newest first
        history.reverse()
except Exception as e:
    st.error(f"Error reading history file: {e}")
    st.stop()

# Filter/Search
search = st.text_input("🔍 Search by topic or answer content", "")

for item in history:
    # Basic data
    ts = datetime.datetime.fromisoformat(item.get("timestamp", ""))
    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
    qid = item.get("question_id", "?")
    topic = item.get("question_topic", "?")
    answer = item.get("student_answer", "")
    feed = item.get("feedback", {})
    verdict = feed.get("verdict", "N/A")
    
    # Filter logic
    if search:
        s = search.lower()
        if s not in topic.lower() and s not in answer.lower() and s not in str(feed).lower():
            continue

    # Card
    with st.expander(f"[{ts_str}] {qid} - {topic} ({verdict})"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**Question**")
            st.info(item.get("question_prompt", ""))
            
            st.markdown("**Your Answer**")
            st.text_area("Answer", value=answer, disabled=True, height=100, key=f"ans_{ts}")
            
        with col2:
            st.markdown("**Feedback**")
            st.write(feed.get("feedback", ""))
            
            st.markdown("**Model Answer**")
            st.success(feed.get("model_answer", ""))
            
            # Raw JSON for copying
            st.divider()
            st.markdown("**Raw Data (Copy for later)**")
            st.code(json.dumps(item, indent=2), language="json")

st.divider()
st.header("🍎 Teacher Tools")
st.markdown("Download this history as a prompt to generate the next set of questions.")

if history:
    prompt_text = f"""
You are an expert Cambridge science tutor.
I have attached the history of a student's recent quiz attempts below in JSON format.

Please analyze their performance, specifically looking for:
1. Recurring misconceptions.
2. Topics where they struggled (low scores).
3. Types of questions they missed (e.g., recall vs application).

Based on this analysis, generate a new set of 10-15 tailored questions to help them improve.
- Focus on their weak areas.
- Include a mix of difficulty levels.
- Format the output as a JSON list of objects with keys: "id", "topic", "marks", "prompt", "answer_type".

Student History JSON:
{json.dumps(history, ensure_ascii=False, indent=2)}
    """.strip()

    st.download_button(
        label="📥 Download Prompt for Next Quiz",
        data=prompt_text,
        file_name="teacher_prompt_next_quiz.txt",
        mime="text/plain",
        help="Upload this file to an LLM (ChatGPT, Claude, Gemini) to generate personalized follow-up questions."
    )
else:
    st.info("No history available to generate a prompt.")
