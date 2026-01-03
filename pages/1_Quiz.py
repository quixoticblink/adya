import streamlit as st
import json
import os
import re
import utils
import auth

# -----------------------------
# Configuration & Setup
# -----------------------------
st.set_page_config(page_title="Grade 7 Chemistry Quiz", page_icon="🧪", layout="centered")

# Auth Check
if not auth.is_authenticated():
    st.warning("🔒 Login Required")
    st.write("Please go to the Home page to sign in.")
    st.stop()

st.title("🧪 Grade 7 Chemistry Quiz")
st.caption("One question per episode • No skipping • Instant feedback")

# API Key
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("Missing OPENAI_API_KEY configuration.")
    st.stop()

client = utils.get_openai_client(OPENAI_API_KEY)

# Load Questions
try:
    QUESTIONS = utils.load_questions("questions.json")
except Exception as e:
    st.error(f"Failed to load questions: {e}")
    st.stop()

if not QUESTIONS:
    st.warning("No questions found.")
    st.stop()

# -----------------------------
# State Management
# -----------------------------
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "feedback" not in st.session_state:
    st.session_state.feedback = {}
if "qa_log" not in st.session_state:
    st.session_state.qa_log = []
if "final_summary" not in st.session_state:
    st.session_state.final_summary = None

def current_question() -> utils.Question:
    return QUESTIONS[st.session_state.idx]

def already_answered(qid: str) -> bool:
    return qid in st.session_state.answers and str(st.session_state.answers[qid]).strip() != ""

def already_has_feedback(qid: str) -> bool:
    return qid in st.session_state.feedback

# -----------------------------
# Quiz Logic
# -----------------------------

# If completed
if st.session_state.idx >= len(QUESTIONS):
    st.success("✅ Quiz completed!")

    if st.session_state.final_summary is None:
        st.info("Generating final summary...")
        try:
            summary = utils.call_openai_for_final_summary(client, st.session_state.qa_log)
            st.session_state.final_summary = summary
            utils.save_summary_to_history(summary)
        except Exception as e:
            st.error(f"Failed to generate final summary: {e}")
            st.stop()

    summary = st.session_state.final_summary

    # Score
    total_score = 0
    total_marks = 0
    for item in st.session_state.qa_log:
        try:
            sb = item.get("feedback", {}).get("score_band", "0")
            matches = re.findall(r"\d+", str(sb))
            if matches:
                total_score += int(matches[0])
            total_marks += item.get("marks", 0)
        except:
            pass

    if total_marks > 0:
        percent = int((total_score / total_marks) * 100)
        st.header(f"🏆 Final Score: {total_score} / {total_marks} ({percent}%)")
    else:
        st.header("🏆 Final Score: —")

    st.subheader("📌 Overall summary")
    st.write(summary.get("overall_summary", ""))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Strengths")
        st.write("\n".join([f"- {x}" for x in (summary.get("strengths") or [])]) or "—")
        st.subheader("🎯 Learning Points")
        st.write("\n".join([f"- {x}" for x in (summary.get("key_learning_points") or [])]) or "—")
    with col2:
        st.subheader("🛠️ Gaps")
        st.write("\n".join([f"- {x}" for x in (summary.get("gaps") or [])]) or "—")
        st.subheader("⚠️ Misconceptions")
        st.write("\n".join([f"- {x}" for x in (summary.get("misconceptions_to_fix") or [])]) or "—")

    st.subheader("🧭 Recommended next topics")
    st.write("\n".join([f"- {x}" for x in (summary.get("recommended_next_topics") or [])]) or "—")

    export = {"qa_log": st.session_state.qa_log, "final_summary": summary}
    st.download_button(
        "Download results (JSON)",
        data=json.dumps(export, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="chemistry_quiz_results.json",
        mime="application/json",
    )
    
    if st.button("Restart Quiz"):
        st.session_state.idx = 0
        st.session_state.answers = {}
        st.session_state.feedback = {}
        st.session_state.qa_log = []
        st.session_state.final_summary = None
        st.rerun()
        
    st.stop()


# Question Interface
q = current_question()
progress = (st.session_state.idx) / len(QUESTIONS)
st.progress(progress, text=f"Progress: {st.session_state.idx}/{len(QUESTIONS)}")

st.subheader(f"Question {st.session_state.idx + 1} of {len(QUESTIONS)}")
st.markdown(f"**{q.topic}** • {q.marks} mark(s)")
st.write(q.prompt)

qid = q.id
default_answer = st.session_state.answers.get(qid, "")

if q.answer_type == "multiline" or len(q.prompt) > 120:
    ans = st.text_area("Your answer", value=default_answer, height=140, key=f"ans_{qid}")
else:
    ans = st.text_input("Your answer", value=default_answer, key=f"ans_{qid}")

ans_clean = (ans or "").strip()

colA, colB = st.columns([1, 1])
with colA:
    submit_disabled = (ans_clean == "") or already_has_feedback(qid)
    if st.button("Submit answer", type="primary", disabled=submit_disabled):
        st.session_state.answers[qid] = ans_clean
        with st.spinner("Getting feedback..."):
            try:
                fb = utils.call_openai_for_feedback(client, q, ans_clean)
                st.session_state.feedback[qid] = fb
                st.session_state.qa_log.append({
                    "id": q.id, "topic": q.topic, "marks": q.marks,
                    "question": q.prompt, "student_answer": ans_clean, "feedback": fb
                })
                utils.save_feedback_to_history(q, ans_clean, fb)
            except Exception as e:
                st.error(f"Failed to get feedback: {e}")
                st.stop()
        st.rerun()

with colB:
    next_disabled = not already_has_feedback(qid)
    if st.button("Next question →", disabled=next_disabled):
        st.session_state.idx += 1
        st.rerun()

if already_has_feedback(qid):
    fb = st.session_state.feedback[qid]
    st.divider()
    st.subheader("🧾 Feedback")
    st.markdown(f"**Verdict:** {fb.get('verdict','—')}  \n**Score:** {fb.get('score_band','—')} / {q.marks}")
    st.markdown("**Quick feedback**"); st.write(fb.get("feedback", ""))
    st.markdown("**Model answer**"); st.info(fb.get("model_answer", ""))
    st.markdown("**Why?**"); st.write(fb.get("why", ""))
    
    if fb.get("misconceptions"):
        st.markdown("**Misconceptions**"); st.write("\n".join([f"- {x}" for x in fb["misconceptions"]]))
    
    vlinks = fb.get("video_links", [])
    if vlinks:
        st.markdown("**Videos**")
        for v in vlinks:
            st.markdown(f"- [{v['query']}]({v['url']})")
            
    st.caption("Click **Next question** to continue.")
