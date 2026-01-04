import streamlit as st
import json
import os
import datetime

import utils
st.set_page_config(page_title="Feedback History", page_icon="📜", layout="wide")
utils.use_custom_css()

import auth
if not auth.is_authenticated():
    st.warning("🔒 Login Required")
    st.write("Please sign in on the Home page.")
    st.stop()

# Admin Password Guard
auth.check_admin_password()

st.title("📜 Feedback History")
st.caption("View past answers and AI feedback.")

try:
    import sheets_db
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False

HISTORY_FILE = "feedback_history.json"

if HAS_SHEETS:
    try:
        history = sheets_db.get_history()
        history.reverse()
    except Exception:
        # Fallback empty list or local file if you prefer mixed mode
        # For now, let's fallback to local file just in case
        history = []
        if os.path.exists(HISTORY_FILE):
             with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
                history.reverse()
else:
    if not os.path.exists(HISTORY_FILE):
        st.info("No history found yet. completes some questions to see them here!")
        st.stop()

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            history.reverse()
    except Exception as e:
        st.error(f"Error reading history file: {e}")
        st.stop()

# --- Delete Helper ---
def delete_record(target_ts: str):
    """Deletes a record with the matching timestamp from the history file."""
    if HAS_SHEETS:
        try:
            sheets_db.delete_history_entry(target_ts)
            st.success("Entry deleted from Sheets.")
            st.rerun()
            return
        except Exception as e:
            # Maybe failed to connect, try local? No, if configured, assume sheets.
            st.error(f"Failed to delete from Sheets: {e}")
            return

    if not os.path.exists(HISTORY_FILE):
        return
        
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Filter out the item
        new_data = [d for d in data if d.get("timestamp") != target_ts]
        
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
            
        st.success("Entry deleted.")
        st.rerun()
    except Exception as e:
        st.error(f"Failed to delete: {e}")

# Filter/Search
SUBJECTS = ["All", "Chemistry", "Biology", "Physics", "Geography", "History"]

col_filter, col_search = st.columns([1, 3])

with col_filter:
    filter_subject = st.selectbox("Subject Filter", SUBJECTS)

with col_search:
    search = st.text_input("Search text", placeholder="Type to search topics or answers...")

for item in history:
    # Safe timestamp parsing
    ts_raw = item.get("timestamp", "")
    try:
        dt = datetime.datetime.fromisoformat(ts_raw)
        ts_str = dt.strftime("%Y-%m-%d %H:%M")
    except:
        ts_str = ts_raw

    # Check type
    record_type = item.get("type", "question")
    item_subject = item.get("subject", "Chemistry") # Assume legacy items are Chemistry

    # 1. Subject Filter
    if filter_subject != "All" and item_subject != filter_subject:
        continue

    if record_type == "summary":
        # --- Summary Card ---
        content = item.get("content", {})
        
        # Filter logic (skip if search doesn't match summary text)
        if search:
            s_text = json.dumps(content).lower()
            if search.lower() not in s_text:
                continue

        with st.expander(f"[{ts_str}] 🏆 Quiz Summary"):
            if st.button("🗑️ Delete Entry", key=f"del_sum_{ts_raw}"):
                delete_record(ts_raw)
            st.divider()
            
            st.markdown(f"**Overall:** {content.get('overall_summary', 'No summary text')}")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**✅ Strengths**")
                st.write("\n".join([f"- {x}" for x in (content.get("strengths") or [])]) or "—")
                st.markdown("**🎯 Key learning points**")
                st.write("\n".join([f"- {x}" for x in (content.get("key_learning_points") or [])]) or "—")

            with c2:
                st.markdown("**🛠️ Gaps**")
                st.write("\n".join([f"- {x}" for x in (content.get("gaps") or [])]) or "—")
                st.markdown("**⚠️ Misconceptions**")
                st.write("\n".join([f"- {x}" for x in (content.get("misconceptions_to_fix") or [])]) or "—")
                
            st.divider()
            st.markdown("**Raw Data**")
            st.code(json.dumps(item, indent=2), language="json")

    else:
        # --- Question Card ---
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

        with st.expander(f"[{ts_str}] {qid} - {topic} ({verdict})"):
            if st.button("🗑️ Delete Entry", key=f"del_q_{ts_raw}"):
                delete_record(ts_raw)
            st.divider()

            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("**Question**")
                st.info(item.get("question_prompt", ""))
                
                st.markdown("**Your Answer**")
                st.text_area("Answer", value=answer, disabled=True, height=100, key=f"ans_{ts_raw}")
                
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
