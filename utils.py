from __future__ import annotations

import json
import os
import re
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import streamlit as st
from openai import OpenAI

# -----------------------------
# Configuration
# -----------------------------
MODEL_FEEDBACK = os.getenv("OPENAI_MODEL_FEEDBACK", "gpt-4o-mini")
MODEL_SUMMARY = os.getenv("OPENAI_MODEL_SUMMARY", "gpt-4o-mini")
TEMPERATURE_FEEDBACK = float(os.getenv("OPENAI_TEMPERATURE_FEEDBACK", "0.4"))
TEMPERATURE_SUMMARY = float(os.getenv("OPENAI_TEMPERATURE_SUMMARY", "0.3"))

def use_custom_css():
    st.markdown("""
        <!-- CSS Updated -->
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        html, body, .stMarkdown, .stText, p {
            font-family: 'Inter', sans-serif;
            color: #111827 !important; /* Force nearly black text */
        }
        
        .stApp {
            background-color: #f9fafb;
        }

        /* Improved Sidebar Contrast */
        [data-testid="stSidebarNav"] span {
            color: #111827 !important;
            font-weight: 500;
        }

        /* Fix Alert Text Contrast (e.g. st.info) */
        div[data-baseweb="notification"] p, div[data-baseweb="notification"] div {
            color: #111827 !important;
        }
        
        /* Modern Buttons */
        .stButton > button {
            border-radius: 12px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.2s ease-in-out;
            border: 1px solid #d1d5db;
            color: #1f2937;
            background-color: white;
            width: 100%; /* Make buttons fill width */
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            border-color: #9ca3af;
            color: #000;
        }
        
        /* Primary Buttons */
        .stButton > button[kind="primary"] {
             background-color: #2563eb;
             color: white;
             border: none;
        }
        
        /* Clean Headers */
        h1 {
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #111827 !important;
        }
        h2, h3 {
            font-weight: 700;
            color: #374151 !important;
        }
        
        /* Cards */
        div[data-testid="stExpander"] {
            background: #ffffff;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        
        /* Custom subject card container styling handled in Home.py via inline CSS, 
           but we can enhance standard containers here if needed */
        
        /* Inputs - Force Light Theme Contrast */
        .stTextInput > div > div > input, 
        .stTextArea > div > div > textarea {
            background-color: #ffffff !important; /* Force white background */
            color: #111827 !important; /* Force black text */
            border-radius: 8px;
            border: 1px solid #d1d5db;
            caret-color: #111827; /* Force cursor color */
        }
        /* Pholder text color */
        ::placeholder {
            color: #6b7280 !important;
            opacity: 1;
        }
        
        /* Ensure input focus state is visible */
        .stTextInput > div > div > input:focus, 
        .stTextArea > div > div > textarea:focus {
            border-color: #2563eb;
            box-shadow: 0 0 0 1px #2563eb;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        </style>
    """, unsafe_allow_html=True)

# -----------------------------
# Data model
# -----------------------------
@dataclass
class Question:
    id: str
    topic: str
    marks: int
    prompt: str
    answer_type: str = "text"

# -----------------------------
# Data retrieval / persistence
# -----------------------------
try:
    import sheets_db
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False

def load_questions(subject: str = "Chemistry") -> List[Question]:
    """Loads questions from Google Sheets (if configured) or local JSON."""
    # Try Sheets first
    if HAS_SHEETS:
        try:
            raw_data = sheets_db.get_questions(subject)
            if raw_data:
                return [Question(**q) for q in raw_data]
        except Exception:
            # Fallthrough to local file
            pass

    # Fallback: Local JSON
    # File naming convention: questions.json (default/legacy) or questions_chemistry.json
    if subject.lower() == "chemistry":
        filepath = "questions.json"
    else:
        filepath = f"questions_{subject.lower()}.json"

    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Question(**q) for q in data]
    return []

# -----------------------------
# Helpers
# -----------------------------
@st.cache_resource
def get_openai_client(api_key: str) -> OpenAI:
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY. Set it in env var or Streamlit secrets.")
    return OpenAI(api_key=api_key)

def youtube_search_link(query: str) -> str:
    q = re.sub(r"\s+", "+", query.strip())
    return f"https://www.youtube.com/results?search_query={q}"

def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    try:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception:
        return None

def save_feedback_to_history(question: Question, answer: str, feedback: Dict[str, Any], subject: str = "Chemistry"):
    """Appends feedback to History (Sheets or local JSON)."""
    record = {
        "subject": subject,
        "question_id": question.id,
        "question_topic": question.topic,
        "question_prompt": question.prompt,
        "student_answer": answer,
        "feedback": feedback
    }
    
    # Try Sheets
    if HAS_SHEETS:
        try:
            sheets_db.append_history("question", record)
            return # Success
        except Exception as e:
            print(f"Sheets Error: {e}")
            st.warning(f"Google Sheets Sync Failed: {e}")
            
    # Fallback: Local JSON
    # Add timestamp locally since Sheets adds it automatically
    record["timestamp"] = datetime.datetime.now().isoformat()
    record["type"] = "question" # Explicit type for unified structure
    
    history_file = "feedback_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(record)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def save_summary_to_history(summary: Dict[str, Any]):
    """Appends final summary to History (Sheets or local JSON)."""
    # Try Sheets
    if HAS_SHEETS:
        try:
            sheets_db.append_history("summary", summary)
            return
        except Exception as e:
            print(f"Sheets Error: {e}")
            st.warning(f"Google Sheets Sync Failed: {e}")

    # Fallback
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "summary",
        "content": summary
    }
    
    history_file = "feedback_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
            
    history.append(record)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def call_openai_for_feedback(
    client: OpenAI,
    question: Question,
    student_answer: str,
    grade_level: str = "Grade 7 Cambridge",
) -> Dict[str, Any]:
    system = (
        "You are a strict but supportive Cambridge lower-secondary science teacher. "
        "Give accurate chemistry explanations for Grade 7. "
        "Be clear, step-by-step, and correct misconceptions. "
        "Do NOT assume the student has prior knowledge beyond Grade 7."
    )

    user = f"""
Create feedback for a student.

Context:
- Level: {grade_level}
- Topic: {question.topic}
- Question ({question.id}, {question.marks} marks): {question.prompt}
- Student answer: {student_answer}

Output MUST be valid JSON with exactly these keys:
{{
  "verdict": "Correct|Partly correct|Incorrect",
  "score_band": "0-{question.marks} (integer as string)",
  "feedback": "Brief, supportive feedback in 3-6 lines",
  "model_answer": "A clear, exam-style ideal answer",
  "why": "Detailed explanation suitable for Grade 7, step-by-step",
  "misconceptions": ["..."],
  "next_steps": ["..."],
  "video_queries": ["3-5 YouTube search queries the student can use"]
}}

Rules:
- Keep the model answer concise but complete for the marks.
- In 'why', explain the science in detail but in simple language.
- If the student is wrong, correct them clearly and kindly.
- video_queries should be specific (e.g., 'Rutherford gold foil experiment explained for kids').
""".strip()

    resp = client.chat.completions.create(
        model=MODEL_FEEDBACK,
        temperature=TEMPERATURE_FEEDBACK,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    content = resp.choices[0].message.content or ""
    parsed = safe_json_loads(content)

    if not parsed:
        parsed = {
            "verdict": "Partly correct",
            "score_band": "0",
            "feedback": "Feedback could not be parsed as JSON. Showing raw response below.",
            "model_answer": "",
            "why": content,
            "misconceptions": [],
            "next_steps": [],
            "video_queries": [],
        }

    vqs = parsed.get("video_queries", []) or []
    parsed["video_links"] = [{"query": q, "url": youtube_search_link(q)} for q in vqs[:6]]

    return parsed

def call_openai_for_final_summary(
    client: OpenAI,
    qa_log: List[Dict[str, Any]],
    grade_level: str = "Grade 7 Cambridge",
) -> Dict[str, Any]:
    system = (
        "You are an expert Cambridge science tutor and assessment designer. "
        "You will analyze student responses and produce a compact, actionable learning plan."
    )

    user = f"""
Analyze the student's full quiz attempt and produce a summary for {grade_level}.

Here is the attempt log as JSON:
{json.dumps(qa_log, ensure_ascii=False, indent=2)}

Output MUST be valid JSON with exactly these keys:
{{
  "overall_summary": "3-6 lines, plain language",
  "strengths": ["..."],
  "gaps": ["..."],
  "misconceptions_to_fix": ["..."],
  "key_learning_points": ["..."],
  "recommended_next_topics": ["..."]
}}

Rules:
- Be specific: reference patterns in the student's answers (e.g., 'confuses concentration with amount').
""".strip()

    resp = client.chat.completions.create(
        model=MODEL_SUMMARY,
        temperature=TEMPERATURE_SUMMARY,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )

    content = resp.choices[0].message.content or ""
    parsed = safe_json_loads(content)

    if not parsed:
        parsed = {
            "overall_summary": "Summary could not be parsed as JSON. Raw output provided.",
            "strengths": [],
            "gaps": [],
            "misconceptions_to_fix": [],
            "key_learning_points": [],
            "recommended_next_topics": [],
            "raw": content,
        }

    return parsed
